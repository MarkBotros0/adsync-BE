"""End-to-end orchestrator: runs all 6 Apify actors for a single job."""
import asyncio
import functools
import logging
from typing import Any, Awaitable, Callable

from app.config import get_settings
from app.database import get_session_local
from app.models.competitor_analysis_result import (
    ACTOR_FACEBOOK_ADS,
    ACTOR_GOOGLE_PLACES,
    ACTOR_GOOGLE_SEARCH,
    ACTOR_INSTAGRAM,
    ACTOR_TIKTOK,
    ACTOR_WEBSITE,
    ALL_ACTOR_KEYS,
)
from app.repositories.competitor_analysis_job import CompetitorAnalysisJobRepository
from app.repositories.competitor_analysis_result import CompetitorAnalysisResultRepository
from app.services.competitor_analysis.apify_client import ApifyClient
from app.services.competitor_analysis.actor_inputs import (
    ACTOR_FACEBOOK_ADS_ID,
    ACTOR_GOOGLE_PLACES_ID,
    ACTOR_GOOGLE_SEARCH_ID,
    ACTOR_INSTAGRAM_ID,
    ACTOR_TIKTOK_ID,
    ACTOR_WEBSITE_ID,
    build_facebook_ads_input,
    build_google_places_input,
    build_google_search_input,
    build_instagram_input,
    build_tiktok_input,
    build_website_input,
)
from app.services.competitor_analysis.normalizers import (
    extract_top_url_from_serp,
    normalize_facebook_ads,
    normalize_google_places,
    normalize_google_search,
    normalize_instagram,
    normalize_tiktok,
    normalize_website,
)


logger = logging.getLogger(__name__)


# Map actor_key -> (apify actor id, default timeout seconds, normalizer)
_INDEPENDENT_ACTORS: dict[str, tuple[str, int, Callable[[list[dict[str, Any]]], tuple[Any, dict[str, Any]]]]] = {
    ACTOR_FACEBOOK_ADS: (ACTOR_FACEBOOK_ADS_ID, 240, normalize_facebook_ads),
    ACTOR_INSTAGRAM: (ACTOR_INSTAGRAM_ID, 240, normalize_instagram),
    ACTOR_TIKTOK: (ACTOR_TIKTOK_ID, 240, normalize_tiktok),
    ACTOR_GOOGLE_PLACES: (ACTOR_GOOGLE_PLACES_ID, 240, normalize_google_places),
}


# ── Public entry point ────────────────────────────────────────────────────────

async def run_analysis(job_id: int, competitor_id: int, brand_id: int, name: str) -> None:
    """Run all 6 Apify actors for the job and persist normalized results.

    Always opens a fresh DB session — must not share the request-bound session.
    Failures of individual actors do not abort the whole job.
    """
    settings = get_settings()
    token = settings.apify_api_token

    if not token:
        _mark_job_failed(job_id, "APIFY_API_TOKEN is not configured on the server")
        return

    client = ApifyClient(token)

    _mark_job_running(job_id)

    # Pre-create the 6 result rows so the frontend can show 6 pending tabs immediately.
    result_ids = _ensure_result_rows(job_id, competitor_id, brand_id)

    try:
        # SERP runs first (also drives the website crawler).
        serp_task = asyncio.create_task(
            _run_one(
                client=client,
                actor_key=ACTOR_GOOGLE_SEARCH,
                actor_id=ACTOR_GOOGLE_SEARCH_ID,
                run_input=build_google_search_input(name),
                normalizer=normalize_google_search,
                job_id=job_id,
                result_id=result_ids[ACTOR_GOOGLE_SEARCH],
                timeout=180,
            )
        )

        independent_tasks: list[asyncio.Task[None]] = []
        for actor_key, (actor_id, timeout, normalizer) in _INDEPENDENT_ACTORS.items():
            run_input = _build_independent_input(actor_key, name)
            if actor_key == ACTOR_FACEBOOK_ADS:
                normalizer = functools.partial(normalize_facebook_ads, brand_name=name)
            independent_tasks.append(
                asyncio.create_task(
                    _run_one(
                        client=client,
                        actor_key=actor_key,
                        actor_id=actor_id,
                        run_input=run_input,
                        normalizer=normalizer,
                        job_id=job_id,
                        result_id=result_ids[actor_key],
                        timeout=timeout,
                    )
                )
            )

        # Wait for SERP — its output gates the website crawler.
        serp_data = await serp_task

        website_task = asyncio.create_task(
            _run_website(
                client=client,
                serp_data=serp_data,
                name=name,
                job_id=job_id,
                result_id=result_ids[ACTOR_WEBSITE],
            )
        )

        await asyncio.gather(*independent_tasks, website_task, return_exceptions=True)

    except Exception as exc:
        logger.exception("Competitor analysis orchestrator crashed: job=%s", job_id)
        _mark_job_failed(job_id, f"Orchestrator crashed: {exc}")
        return

    _finalize_job(job_id)


# ── Single-actor retry (per-tab refresh) ──────────────────────────────────────

async def run_single_actor(
    job_id: int,
    result_id: int,
    competitor_id: int,
    brand_id: int,
    name: str,
    actor_key: str,
) -> None:
    """Re-run one actor inside an existing job.

    Used by the per-tab Retry button. Updates the existing result row in place
    and re-finalizes the job when done.
    """
    settings = get_settings()
    token = settings.apify_api_token

    if not token:
        _record_actor_failure(job_id, result_id, "APIFY_API_TOKEN is not configured on the server")
        _finalize_job(job_id)
        return

    client = ApifyClient(token)

    try:
        if actor_key == ACTOR_GOOGLE_SEARCH:
            await _run_one(
                client=client,
                actor_key=actor_key,
                actor_id=ACTOR_GOOGLE_SEARCH_ID,
                run_input=build_google_search_input(name),
                normalizer=normalize_google_search,
                job_id=job_id,
                result_id=result_id,
                timeout=180,
            )
        elif actor_key == ACTOR_WEBSITE:
            # Reuse the most recent google_search result for the same competitor
            # to find a URL; if not available, fail fast with a friendly message.
            top_url = _latest_serp_top_url(competitor_id)
            if not top_url:
                _record_actor_failure(
                    job_id,
                    result_id,
                    "Cannot retry Website without a Google Search result. "
                    "Refresh the SERP tab first or run a full Refresh.",
                )
            else:
                await _run_one(
                    client=client,
                    actor_key=actor_key,
                    actor_id=ACTOR_WEBSITE_ID,
                    run_input=build_website_input(top_url),
                    normalizer=normalize_website,
                    job_id=job_id,
                    result_id=result_id,
                    timeout=300,
                )
        elif actor_key in _INDEPENDENT_ACTORS:
            actor_id, timeout, normalizer = _INDEPENDENT_ACTORS[actor_key]
            if actor_key == ACTOR_FACEBOOK_ADS:
                normalizer = functools.partial(normalize_facebook_ads, brand_name=name)
            await _run_one(
                client=client,
                actor_key=actor_key,
                actor_id=actor_id,
                run_input=_build_independent_input(actor_key, name),
                normalizer=normalizer,
                job_id=job_id,
                result_id=result_id,
                timeout=timeout,
            )
        else:
            _record_actor_failure(job_id, result_id, f"Unknown actor: {actor_key}")
    except Exception as exc:
        logger.exception("Single-actor retry crashed: actor=%s job=%s", actor_key, job_id)
        _record_actor_failure(job_id, result_id, f"Retry crashed: {exc}")

    _finalize_job(job_id)


def _latest_serp_top_url(competitor_id: int) -> str | None:
    """Look up the most recent completed Google Search result for this competitor
    and return its top organic URL, if any."""
    db = get_session_local()()
    try:
        from app.models.competitor_analysis_result import (
            ACTOR_GOOGLE_SEARCH as _SERP_KEY,
            CompetitorAnalysisResultModel,
            RESULT_STATUS_COMPLETED,
        )
        row = (
            db.query(CompetitorAnalysisResultModel)
            .filter(
                CompetitorAnalysisResultModel.competitor_id == competitor_id,
                CompetitorAnalysisResultModel.actor_key == _SERP_KEY,
                CompetitorAnalysisResultModel.status == RESULT_STATUS_COMPLETED,
                CompetitorAnalysisResultModel.deleted_at.is_(None),
            )
            .order_by(CompetitorAnalysisResultModel.finished_at.desc())
            .first()
        )
        if not row or not row.data:
            return None
        return extract_top_url_from_serp(row.data)
    finally:
        db.close()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_independent_input(actor_key: str, name: str) -> dict[str, Any]:
    if actor_key == ACTOR_FACEBOOK_ADS:
        return build_facebook_ads_input(name)
    if actor_key == ACTOR_INSTAGRAM:
        return build_instagram_input(name)
    if actor_key == ACTOR_TIKTOK:
        return build_tiktok_input(name)
    if actor_key == ACTOR_GOOGLE_PLACES:
        return build_google_places_input(name)
    raise ValueError(f"Unsupported independent actor: {actor_key}")


async def _run_one(
    *,
    client: ApifyClient,
    actor_key: str,
    actor_id: str,
    run_input: dict[str, Any],
    normalizer: Callable[[list[dict[str, Any]]], tuple[Any, dict[str, Any]]],
    job_id: int,
    result_id: int,
    timeout: int,
) -> Any:
    """Run a single actor end-to-end: mark running → call → normalize → save.

    Returns the normalized data on success (so chained actors can use it),
    or ``None`` on failure. Exceptions are caught and logged.
    """
    db = get_session_local()()
    try:
        CompetitorAnalysisResultRepository(db).mark_running(result_id)
    finally:
        db.close()

    try:
        items = await asyncio.wait_for(
            client.run_actor(actor_id=actor_id, run_input=run_input, timeout_seconds=timeout),
            timeout=timeout + 60,
        )
    except asyncio.TimeoutError:
        _record_actor_failure(job_id, result_id, f"timeout after {timeout + 60}s")
        return None
    except Exception as exc:  # noqa: BLE001 — we want to catch *anything* and isolate failure
        logger.warning("Actor %s failed for job %s: %s", actor_id, job_id, exc)
        _record_actor_failure(job_id, result_id, str(exc))
        return None

    try:
        data, summary = normalizer(items)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Normalizer for %s failed", actor_key)
        _record_actor_failure(job_id, result_id, f"normalizer error: {exc}")
        return None

    _record_actor_success(job_id, result_id, data, summary)
    return data


async def _run_website(
    *,
    client: ApifyClient,
    serp_data: Any,
    name: str,
    job_id: int,
    result_id: int,
) -> None:
    """Run the website crawler against the top SERP result."""
    if not isinstance(serp_data, dict):
        _record_actor_failure(job_id, result_id, "no SERP data — website crawl skipped")
        return

    top_url = extract_top_url_from_serp(serp_data)
    if not top_url:
        _record_actor_failure(job_id, result_id, "no usable URL in SERP results")
        return

    await _run_one(
        client=client,
        actor_key=ACTOR_WEBSITE,
        actor_id=ACTOR_WEBSITE_ID,
        run_input=build_website_input(top_url),
        normalizer=normalize_website,
        job_id=job_id,
        result_id=result_id,
        timeout=300,
    )


def _ensure_result_rows(job_id: int, competitor_id: int, brand_id: int) -> dict[str, int]:
    """Create one result row per actor; return ``{actor_key: result_id}``."""
    db = get_session_local()()
    try:
        repo = CompetitorAnalysisResultRepository(db)
        out: dict[str, int] = {}
        for key in ALL_ACTOR_KEYS:
            existing = repo.get_by_job_and_actor(job_id, key)
            if existing:
                out[key] = existing.id
            else:
                row = repo.create_pending(
                    job_id=job_id,
                    competitor_id=competitor_id,
                    brand_id=brand_id,
                    actor_key=key,
                )
                out[key] = row.id
        return out
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


def _mark_job_failed(job_id: int, message: str) -> None:
    db = get_session_local()()
    try:
        CompetitorAnalysisJobRepository(db).mark_failed(job_id, message)
    finally:
        db.close()


def _record_actor_success(job_id: int, result_id: int, data: Any, summary: dict[str, Any]) -> None:
    db = get_session_local()()
    try:
        CompetitorAnalysisResultRepository(db).mark_completed(result_id, data, summary)
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
