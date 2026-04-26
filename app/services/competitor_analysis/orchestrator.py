"""Single-actor orchestrator.

Each scraper now runs as its own job (one row in ``competitor_analysis_jobs``
with ``actors_total=1``). The whole "refresh all six" flow is gone — users
configure per-actor targets and explicitly run each scraper.
"""
import asyncio
import functools
import logging
from typing import Any, Callable

from app.config import get_settings
from app.database import get_session_local
from app.models.competitor_analysis_result import (
    ACTOR_FACEBOOK_ADS,
    ACTOR_GOOGLE_PLACES,
    ACTOR_GOOGLE_SEARCH,
    ACTOR_INSTAGRAM,
    ACTOR_TIKTOK,
    ACTOR_WEBSITE,
)
from app.repositories.apify_run import ApifyRunRepository
from app.repositories.competitor_analysis_job import CompetitorAnalysisJobRepository
from app.repositories.competitor_analysis_result import CompetitorAnalysisResultRepository
from app.repositories.competitor_target import CompetitorTargetRepository
from app.services.competitor_analysis.actor_inputs import (
    ACTOR_FACEBOOK_ADS_ID,
    ACTOR_GOOGLE_PLACES_ID,
    ACTOR_GOOGLE_SEARCH_ID,
    ACTOR_INSTAGRAM_ID,
    ACTOR_TIKTOK_ID,
    ACTOR_WEBSITE_ID,
    Target,
    build_facebook_ads_input,
    build_google_places_input,
    build_google_search_input,
    build_instagram_input,
    build_tiktok_input,
    build_website_input,
)
from app.services.competitor_analysis.apify_client import ApifyClient, RunOutcome
from app.services.competitor_analysis.normalizers import (
    normalize_facebook_ads,
    normalize_google_places,
    normalize_google_search,
    normalize_instagram,
    normalize_tiktok,
    normalize_website,
)
from app.utils.exceptions import ApifyActorError


logger = logging.getLogger(__name__)


# Actor-key → (apify actor id, default timeout, input builder, normalizer)
_ACTOR_REGISTRY: dict[
    str,
    tuple[
        str,
        int,
        Callable[[Target], dict[str, Any]],
        Callable[[list[dict[str, Any]]], tuple[Any, dict[str, Any]]],
    ],
] = {
    ACTOR_FACEBOOK_ADS: (ACTOR_FACEBOOK_ADS_ID, 240, build_facebook_ads_input, normalize_facebook_ads),
    ACTOR_INSTAGRAM:    (ACTOR_INSTAGRAM_ID,    300, build_instagram_input,    normalize_instagram),
    ACTOR_TIKTOK:       (ACTOR_TIKTOK_ID,       300, build_tiktok_input,       normalize_tiktok),
    ACTOR_GOOGLE_SEARCH:(ACTOR_GOOGLE_SEARCH_ID,180, build_google_search_input,normalize_google_search),
    ACTOR_GOOGLE_PLACES:(ACTOR_GOOGLE_PLACES_ID,300, build_google_places_input,normalize_google_places),
    ACTOR_WEBSITE:      (ACTOR_WEBSITE_ID,      360, build_website_input,      normalize_website),
}


# ── Public entry points ───────────────────────────────────────────────────────

async def run_target(
    *,
    job_id: int,
    result_id: int,
    target_id: int,
    competitor_id: int,
    brand_id: int,
    actor_key: str,
    target_value: str,
    target_type: str,
    competitor_name: str,
) -> None:
    """Run one scraper end-to-end and persist results + cost.

    Always opens a fresh DB session — must not share the request-bound session.
    Cost-ledger writes are best-effort: if Apify's metadata endpoint fails we
    still record the result.
    """
    settings = get_settings()
    token = settings.apify_api_token
    if not token:
        _record_actor_failure(job_id, result_id, "APIFY_API_TOKEN is not configured on the server")
        _finalize_job(job_id)
        return

    if actor_key not in _ACTOR_REGISTRY:
        _record_actor_failure(job_id, result_id, f"Unknown actor: {actor_key}")
        _finalize_job(job_id)
        return

    actor_id, timeout, build_input, normalizer = _ACTOR_REGISTRY[actor_key]

    if actor_key == ACTOR_FACEBOOK_ADS:
        normalizer = functools.partial(normalize_facebook_ads, brand_name=competitor_name)

    target = Target(actor_key=actor_key, target_value=target_value, target_type=target_type)
    try:
        run_input = build_input(target)
    except Exception as exc:  # noqa: BLE001
        _record_actor_failure(job_id, result_id, f"invalid target: {exc}")
        _finalize_job(job_id)
        return

    client = ApifyClient(token)

    # Open a ledger row up-front so we can record cost even if the run fails.
    ledger_id = _start_ledger(
        brand_id=brand_id,
        competitor_id=competitor_id,
        result_id=result_id,
        actor_key=actor_key,
    )

    _mark_result_running(result_id)
    _mark_job_running(job_id)

    try:
        outcome = await asyncio.wait_for(
            client.run_actor(actor_id=actor_id, run_input=run_input, timeout_seconds=timeout),
            timeout=timeout + 60,
        )
    except asyncio.CancelledError:
        # Worker was cancelled (server shutdown, reload). Mark the row failed
        # synchronously so the UI shows the failure on next read instead of a
        # frozen "running" state, then re-raise so asyncio cleanup runs.
        logger.warning("Actor %s cancelled mid-run (job=%s)", actor_id, job_id)
        _record_actor_failure(
            job_id,
            result_id,
            "Run interrupted — the server was stopped or restarted before this scraper finished. Run the scraper again to retry.",
        )
        try:
            CompetitorAnalysisJobRepository(get_session_local()()).mark_failed(
                job_id, "Server shutdown interrupted this scrape."
            )
        except Exception:  # noqa: BLE001
            pass
        _mark_target_run(target_id, cost_usd=None)
        raise
    except asyncio.TimeoutError:
        _record_actor_failure(job_id, result_id, f"timeout after {timeout + 60}s")
        await _finalize_ledger(client, ledger_id, run_id=None, success=False)
        _finalize_job(job_id)
        _mark_target_run(target_id, cost_usd=None)
        return
    except ApifyActorError as exc:
        logger.warning("Actor %s failed for job %s: %s", actor_id, job_id, exc)
        _record_actor_failure(job_id, result_id, str(exc))
        await _finalize_ledger(client, ledger_id, run_id=exc.run_id, success=False)
        _mark_target_run(target_id, cost_usd=None)
        _finalize_job(job_id)
        return
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected actor failure: actor=%s job=%s", actor_id, job_id)
        _record_actor_failure(job_id, result_id, f"unexpected error: {exc}")
        await _finalize_ledger(client, ledger_id, run_id=None, success=False)
        _mark_target_run(target_id, cost_usd=None)
        _finalize_job(job_id)
        return

    try:
        data, summary = normalizer(outcome.items)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Normalizer for %s failed", actor_key)
        _record_actor_failure(job_id, result_id, f"normalizer error: {exc}")
        await _finalize_ledger(client, ledger_id, run_id=outcome.run_id, success=False)
        _mark_target_run(target_id, cost_usd=None)
        _finalize_job(job_id)
        return

    _record_actor_success(job_id, result_id, data, summary, apify_run_id=outcome.run_id)
    cost_usd = await _finalize_ledger(client, ledger_id, run_id=outcome.run_id, success=True)
    _mark_target_run(target_id, cost_usd=cost_usd)
    _finalize_job(job_id)


# ── DB helpers ────────────────────────────────────────────────────────────────

def _mark_result_running(result_id: int) -> None:
    db = get_session_local()()
    try:
        CompetitorAnalysisResultRepository(db).mark_running(result_id)
    finally:
        db.close()


def _mark_job_running(job_id: int) -> None:
    db = get_session_local()()
    try:
        CompetitorAnalysisJobRepository(db).mark_running(job_id)
    finally:
        db.close()


def _finalize_job(job_id: int) -> None:
    db = get_session_local()()
    try:
        CompetitorAnalysisJobRepository(db).finalize(job_id)
    finally:
        db.close()


def _record_actor_success(
    job_id: int,
    result_id: int,
    data: Any,
    summary: dict[str, Any],
    *,
    apify_run_id: str | None,
) -> None:
    db = get_session_local()()
    try:
        repo = CompetitorAnalysisResultRepository(db)
        if apify_run_id:
            row = repo.get(result_id)
            if row:
                row.apify_run_id = apify_run_id
                db.commit()
        repo.mark_completed(result_id, data, summary)
        CompetitorAnalysisJobRepository(db).increment_done(job_id)
    finally:
        db.close()


def _record_actor_failure(job_id: int, result_id: int, error: str) -> None:
    db = get_session_local()()
    try:
        CompetitorAnalysisResultRepository(db).mark_failed(result_id, error)
        CompetitorAnalysisJobRepository(db).increment_failed(job_id)
    finally:
        db.close()


def _start_ledger(
    *,
    brand_id: int,
    competitor_id: int,
    result_id: int,
    actor_key: str,
) -> int:
    db = get_session_local()()
    try:
        run = ApifyRunRepository(db).start_run(
            brand_id=brand_id,
            competitor_id=competitor_id,
            result_id=result_id,
            actor_key=actor_key,
        )
        return run.id
    finally:
        db.close()


async def _finalize_ledger(
    client: ApifyClient,
    ledger_id: int,
    *,
    run_id: str | None,
    success: bool,
) -> float | None:
    """Best-effort: fetch run meta and write the cost row. Returns cost USD."""
    meta = None
    if run_id:
        try:
            meta = await client.fetch_run_meta(run_id)
        except Exception:  # noqa: BLE001
            logger.exception("fetch_run_meta crashed; skipping cost capture")

    db = get_session_local()()
    try:
        repo = ApifyRunRepository(db)
        if success:
            repo.finalize_success(
                ledger_id,
                apify_run_id=meta.run_id if meta else run_id,
                compute_units=meta.compute_units if meta else None,
                usage_total_usd=meta.usage_total_usd if meta else None,
                dataset_id=meta.dataset_id if meta else None,
            )
        else:
            repo.finalize_failure(
                ledger_id,
                apify_run_id=meta.run_id if meta else run_id,
                compute_units=meta.compute_units if meta else None,
                usage_total_usd=meta.usage_total_usd if meta else None,
            )
    finally:
        db.close()

    return meta.usage_total_usd if meta else None


def _mark_target_run(target_id: int, cost_usd: float | None) -> None:
    db = get_session_local()()
    try:
        CompetitorTargetRepository(db).mark_run(target_id, cost_usd)
    finally:
        db.close()
