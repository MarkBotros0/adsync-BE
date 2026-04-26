"""Competitor Analysis HTTP router."""
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.database import get_session_local
from app.dependencies import require_brand
from app.models.competitor_analysis_job import JOB_ACTIVE_STATUSES
from app.models.competitor_analysis_result import ALL_ACTOR_KEYS
from app.models.competitor_target import (
    ALL_TARGET_TYPES,
    CompetitorTargetModel,
)
from app.repositories.apify_run import ApifyRunRepository
from app.repositories.competitor import CompetitorRepository, normalize_slug
from app.repositories.competitor_analysis_job import CompetitorAnalysisJobRepository
from app.repositories.competitor_analysis_result import CompetitorAnalysisResultRepository
from app.repositories.competitor_target import CompetitorTargetRepository
from app.routers.competitors.schemas import (
    ActorResultOut,
    ActorSummaryRequest,
    BudgetSnapshot,
    CompetitorCreateRequest,
    CompetitorOut,
    CompetitorTargetIn,
    CompetitorTargetOut,
    EstimatedCostOut,
    JobCreatedOut,
    JobStatusOut,
    JobSummary,
)
from app.services.budget import check_budget, is_super
from app.services.competitor_analysis.actor_inputs import (
    ALLOWED_TARGET_TYPES,
    DEFAULT_TARGET_TYPES,
)
from app.services.competitor_analysis.aggregations import summarize
from app.services.competitor_analysis.cost_estimator import estimate
from app.services.competitor_analysis.scheduler import enqueue_target_run


router = APIRouter(prefix="/competitors", tags=["Competitor Analysis"])
logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_brand_id(brand) -> int:
    if not brand or not getattr(brand, "id", None):
        raise HTTPException(status_code=403, detail="Brand context required")
    return int(brand.id)


def _competitor_to_out(
    competitor,
    *,
    last_job=None,
    targets: list[CompetitorTargetModel] | None = None,
    summaries: dict[str, dict[str, Any]] | None = None,
) -> CompetitorOut:
    return CompetitorOut(
        id=competitor.id,
        name=competitor.name,
        slug=competitor.slug,
        created_at=competitor.created_at,
        updated_at=competitor.updated_at,
        last_job=JobSummary.model_validate(last_job) if last_job else None,
        targets=[CompetitorTargetOut.model_validate(t) for t in (targets or [])],
        summaries=summaries,
    )


def _validate_target(actor_key: str, target_type: str) -> None:
    if actor_key not in ALL_ACTOR_KEYS:
        raise HTTPException(status_code=422, detail=f"Unknown actor key: {actor_key}")
    if target_type not in ALL_TARGET_TYPES:
        raise HTTPException(status_code=422, detail=f"Unknown target type: {target_type}")
    allowed = ALLOWED_TARGET_TYPES.get(actor_key, ())
    if allowed and target_type not in allowed:
        raise HTTPException(
            status_code=422,
            detail=f"Actor {actor_key} only accepts target types: {', '.join(allowed)}",
        )


def _build_summaries(results: list) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for r in results:
        if r.summary:
            out[r.actor_key] = r.summary
    return out


# ── List / get / create / delete ──────────────────────────────────────────────

@router.get("", status_code=200)
async def list_competitors(brand=Depends(require_brand)) -> dict[str, Any]:
    brand_id = _require_brand_id(brand)
    db = get_session_local()()
    try:
        comp_repo = CompetitorRepository(db)
        job_repo = CompetitorAnalysisJobRepository(db)
        res_repo = CompetitorAnalysisResultRepository(db)
        target_repo = CompetitorTargetRepository(db)

        competitors = comp_repo.list_by_brand(brand_id)
        out: list[CompetitorOut] = []
        for comp in competitors:
            last_job = job_repo.latest_for_competitor(comp.id)
            summaries: dict[str, dict[str, Any]] | None = None
            if last_job:
                results = res_repo.list_by_job(last_job.id)
                summaries = _build_summaries(results) or None
            targets = target_repo.list_for_competitor(comp.id)
            out.append(_competitor_to_out(
                comp, last_job=last_job, targets=targets, summaries=summaries,
            ))

        return {
            "success": True,
            "data": {
                "total": len(out),
                "competitors": [c.model_dump(mode="json") for c in out],
            },
        }
    finally:
        db.close()


@router.post("", status_code=201)
async def create_competitor(
    payload: CompetitorCreateRequest,
    brand=Depends(require_brand),
) -> dict[str, Any]:
    """Create a competitor with per-actor targets. **No auto-run** — the user
    must explicitly run each scraper via ``/actors/{key}/run`` after creation."""
    brand_id = _require_brand_id(brand)

    for t in payload.targets:
        _validate_target(t.actor_key, t.target_type)

    db = get_session_local()()
    try:
        comp_repo = CompetitorRepository(db)
        target_repo = CompetitorTargetRepository(db)

        slug = normalize_slug(payload.name)
        if not slug:
            raise HTTPException(status_code=422, detail="Name must contain at least one alphanumeric character")
        if comp_repo.find_by_slug(brand_id, slug):
            raise HTTPException(status_code=409, detail="Competitor with this name already exists")

        competitor = comp_repo.create_for_brand(brand_id, payload.name)

        for t in payload.targets:
            target_repo.upsert(
                brand_id=brand_id,
                competitor_id=competitor.id,
                actor_key=t.actor_key,
                target_value=t.target_value.strip(),
                target_type=t.target_type,
                is_enabled=t.is_enabled,
            )

        targets = target_repo.list_for_competitor(competitor.id)
        payload_out = _competitor_to_out(
            competitor, targets=targets,
        ).model_dump(mode="json")
    finally:
        db.close()

    return {"success": True, "data": {"competitor": payload_out}}


@router.get("/{competitor_id}", status_code=200)
async def get_competitor(
    competitor_id: int,
    brand=Depends(require_brand),
) -> dict[str, Any]:
    brand_id = _require_brand_id(brand)
    db = get_session_local()()
    try:
        comp_repo = CompetitorRepository(db)
        job_repo = CompetitorAnalysisJobRepository(db)
        res_repo = CompetitorAnalysisResultRepository(db)
        target_repo = CompetitorTargetRepository(db)

        competitor = comp_repo.get_for_brand(brand_id, competitor_id)
        if not competitor:
            raise HTTPException(status_code=404, detail="Competitor not found")

        last_job = job_repo.latest_for_competitor(competitor.id)
        summaries = None
        if last_job:
            summaries = _build_summaries(res_repo.list_by_job(last_job.id)) or None
        targets = target_repo.list_for_competitor(competitor.id)

        return {
            "success": True,
            "data": _competitor_to_out(
                competitor,
                last_job=last_job,
                targets=targets,
                summaries=summaries,
            ).model_dump(mode="json"),
        }
    finally:
        db.close()


@router.delete("/{competitor_id}", status_code=200)
async def delete_competitor(
    competitor_id: int,
    brand=Depends(require_brand),
) -> dict[str, Any]:
    brand_id = _require_brand_id(brand)
    db = get_session_local()()
    try:
        ok = CompetitorRepository(db).soft_delete_for_brand(brand_id, competitor_id)
    finally:
        db.close()

    if not ok:
        raise HTTPException(status_code=404, detail="Competitor not found")
    return {"success": True, "message": "Competitor deleted"}


# ── Targets ───────────────────────────────────────────────────────────────────

@router.get("/{competitor_id}/targets", status_code=200)
async def list_targets(
    competitor_id: int,
    brand=Depends(require_brand),
) -> dict[str, Any]:
    brand_id = _require_brand_id(brand)
    db = get_session_local()()
    try:
        comp_repo = CompetitorRepository(db)
        target_repo = CompetitorTargetRepository(db)

        competitor = comp_repo.get_for_brand(brand_id, competitor_id)
        if not competitor:
            raise HTTPException(status_code=404, detail="Competitor not found")

        targets = target_repo.list_for_competitor(competitor.id)
        return {
            "success": True,
            "data": {
                "targets": [
                    CompetitorTargetOut.model_validate(t).model_dump(mode="json")
                    for t in targets
                ],
                "default_target_types": DEFAULT_TARGET_TYPES,
                "allowed_target_types": {k: list(v) for k, v in ALLOWED_TARGET_TYPES.items()},
            },
        }
    finally:
        db.close()


@router.put("/{competitor_id}/targets/{actor_key}", status_code=200)
async def upsert_target(
    competitor_id: int,
    actor_key: str,
    payload: CompetitorTargetIn,
    brand=Depends(require_brand),
) -> dict[str, Any]:
    brand_id = _require_brand_id(brand)

    if payload.actor_key != actor_key:
        raise HTTPException(status_code=422, detail="Actor key in path/body must match")
    _validate_target(actor_key, payload.target_type)

    db = get_session_local()()
    try:
        comp_repo = CompetitorRepository(db)
        competitor = comp_repo.get_for_brand(brand_id, competitor_id)
        if not competitor:
            raise HTTPException(status_code=404, detail="Competitor not found")

        target = CompetitorTargetRepository(db).upsert(
            brand_id=brand_id,
            competitor_id=competitor.id,
            actor_key=payload.actor_key,
            target_value=payload.target_value.strip(),
            target_type=payload.target_type,
            is_enabled=payload.is_enabled,
        )
        return {
            "success": True,
            "data": CompetitorTargetOut.model_validate(target).model_dump(mode="json"),
        }
    finally:
        db.close()


@router.delete("/{competitor_id}/targets/{actor_key}", status_code=200)
async def delete_target(
    competitor_id: int,
    actor_key: str,
    brand=Depends(require_brand),
) -> dict[str, Any]:
    brand_id = _require_brand_id(brand)
    db = get_session_local()()
    try:
        comp_repo = CompetitorRepository(db)
        competitor = comp_repo.get_for_brand(brand_id, competitor_id)
        if not competitor:
            raise HTTPException(status_code=404, detail="Competitor not found")
        ok = CompetitorTargetRepository(db).soft_delete_for_competitor(competitor.id, actor_key)
    finally:
        db.close()

    if not ok:
        raise HTTPException(status_code=404, detail="Target not found")
    return {"success": True, "message": "Target removed"}


# ── Run a single actor ────────────────────────────────────────────────────────

@router.post("/{competitor_id}/actors/{actor_key}/run", status_code=202)
async def run_actor(
    competitor_id: int,
    actor_key: str,
    background_tasks: BackgroundTasks,
    brand=Depends(require_brand),
) -> dict[str, Any]:
    brand_id = _require_brand_id(brand)
    if actor_key not in ALL_ACTOR_KEYS:
        raise HTTPException(status_code=422, detail=f"Unknown actor key: {actor_key}")

    # Budget gate
    org_id = getattr(brand, "organization_id", None)
    if not is_super(brand):
        budget = check_budget(brand_id, org_id)
        if budget.will_block:
            raise HTTPException(
                status_code=402,
                detail={
                    "message": "Monthly compute-unit budget exceeded for this organization.",
                    "used_compute_units": budget.used_compute_units,
                    "monthly_compute_unit_budget": budget.monthly_compute_unit_budget,
                },
            )

    db = get_session_local()()
    try:
        comp_repo = CompetitorRepository(db)
        target_repo = CompetitorTargetRepository(db)
        job_repo = CompetitorAnalysisJobRepository(db)
        res_repo = CompetitorAnalysisResultRepository(db)

        # Auto-heal stuck rows so a dead worker can't block re-runs forever.
        res_repo.heal_stuck_for_competitor(competitor_id)

        competitor = comp_repo.get_for_brand(brand_id, competitor_id)
        if not competitor:
            raise HTTPException(status_code=404, detail="Competitor not found")

        target = target_repo.get_for_competitor(competitor.id, actor_key)
        if not target or not target.is_enabled or not target.target_value.strip():
            raise HTTPException(
                status_code=422,
                detail="No enabled target configured for this scraper. Add one before running.",
            )

        # Reject only if the latest result for THIS actor is still alive after
        # the heal pass — a stuck row from a dead worker shouldn't block re-runs.
        latest_job = job_repo.latest_for_competitor(competitor.id)
        if latest_job and latest_job.status in JOB_ACTIVE_STATUSES:
            latest_result = res_repo.get_by_job_and_actor(latest_job.id, actor_key)
            if latest_result and latest_result.status in ("pending", "running"):
                raise HTTPException(
                    status_code=409,
                    detail="This scraper is already running for the competitor.",
                )

        job = job_repo.create_pending(
            brand_id=brand_id,
            competitor_id=competitor.id,
            actors_total=1,
        )
        result = res_repo.create_pending(
            job_id=job.id,
            competitor_id=competitor.id,
            brand_id=brand_id,
            actor_key=actor_key,
        )

        # Snapshot before closing the session.
        job_id = job.id
        result_id = result.id
        target_id = target.id
        target_value = target.target_value
        target_type = target.target_type
        competitor_name = competitor.name
    finally:
        db.close()

    enqueue_target_run(
        background_tasks,
        job_id=job_id,
        result_id=result_id,
        target_id=target_id,
        competitor_id=competitor_id,
        brand_id=brand_id,
        actor_key=actor_key,
        target_value=target_value,
        target_type=target_type,
        competitor_name=competitor_name,
    )

    est = estimate(brand_id, actor_key)
    return {
        "success": True,
        "data": JobCreatedOut(
            job_id=job_id,
            status="pending",
            actor_key=actor_key,
            estimated_cost_usd=est.avg_usage_usd,
        ).model_dump(),
    }


@router.get("/{competitor_id}/actors/{actor_key}/estimate", status_code=200)
async def estimate_actor(
    competitor_id: int,
    actor_key: str,
    brand=Depends(require_brand),
) -> dict[str, Any]:
    brand_id = _require_brand_id(brand)
    if actor_key not in ALL_ACTOR_KEYS:
        raise HTTPException(status_code=422, detail=f"Unknown actor key: {actor_key}")
    est = estimate(brand_id, actor_key)
    return {
        "success": True,
        "data": EstimatedCostOut(
            actor_key=est.actor_key,
            avg_compute_units=est.avg_compute_units,
            avg_usage_usd=est.avg_usage_usd,
            low_usd=est.low_usd,
            high_usd=est.high_usd,
            samples=est.samples,
            basis=est.basis,
        ).model_dump(),
    }


@router.post("/{competitor_id}/actors/{actor_key}/summary", status_code=200)
async def actor_summary(
    competitor_id: int,
    actor_key: str,
    payload: ActorSummaryRequest,
    brand=Depends(require_brand),
) -> dict[str, Any]:
    brand_id = _require_brand_id(brand)
    if actor_key not in ALL_ACTOR_KEYS:
        raise HTTPException(status_code=422, detail=f"Unknown actor key: {actor_key}")

    db = get_session_local()()
    try:
        comp_repo = CompetitorRepository(db)
        job_repo = CompetitorAnalysisJobRepository(db)
        res_repo = CompetitorAnalysisResultRepository(db)

        competitor = comp_repo.get_for_brand(brand_id, competitor_id)
        if not competitor:
            raise HTTPException(status_code=404, detail="Competitor not found")

        job = job_repo.latest_completed_for_competitor(competitor.id) or job_repo.latest_for_competitor(competitor.id)
        if not job:
            return {"success": True, "data": {"actor_key": actor_key, "summary": {}}}

        result = res_repo.get_by_job_and_actor(job.id, actor_key)
        raw = result.data if result else None
    finally:
        db.close()

    summary = summarize(actor_key, raw, payload.filters)
    return {"success": True, "data": {"actor_key": actor_key, "summary": summary}}


@router.get("/{competitor_id}/results/{actor_key}", status_code=200)
async def get_actor_results(
    competitor_id: int,
    actor_key: str,
    brand=Depends(require_brand),
) -> dict[str, Any]:
    brand_id = _require_brand_id(brand)
    if actor_key not in ALL_ACTOR_KEYS:
        raise HTTPException(status_code=422, detail=f"Unknown actor key: {actor_key}")

    db = get_session_local()()
    try:
        comp_repo = CompetitorRepository(db)
        job_repo = CompetitorAnalysisJobRepository(db)
        res_repo = CompetitorAnalysisResultRepository(db)

        competitor = comp_repo.get_for_brand(brand_id, competitor_id)
        if not competitor:
            raise HTTPException(status_code=404, detail="Competitor not found")

        res_repo.heal_stuck_for_competitor(competitor.id)

        # Find the latest result row for THIS actor across all jobs (not just
        # the latest job — the latest job may be for a different actor).
        from app.models.competitor_analysis_result import CompetitorAnalysisResultModel
        result = (
            db.query(CompetitorAnalysisResultModel)
            .filter(
                CompetitorAnalysisResultModel.competitor_id == competitor.id,
                CompetitorAnalysisResultModel.actor_key == actor_key,
                CompetitorAnalysisResultModel.deleted_at.is_(None),
            )
            .order_by(CompetitorAnalysisResultModel.created_at.desc())
            .first()
        )
        job = job_repo.latest_for_competitor(competitor.id)
        result_payload: ActorResultOut
        if not result:
            result_payload = ActorResultOut(actor_key=actor_key, status="idle")
        else:
            result_payload = ActorResultOut(
                actor_key=result.actor_key,
                status=result.status,
                summary=result.summary,
                data=result.data,
                error=result.error,
                started_at=result.started_at,
                finished_at=result.finished_at,
            )

        return {
            "success": True,
            "data": {
                "actor_key": actor_key,
                "result": result_payload.model_dump(mode="json"),
                "job": JobSummary.model_validate(job).model_dump(mode="json") if job else None,
            },
        }
    finally:
        db.close()


# ── Job status & overview results ─────────────────────────────────────────────

@router.get("/jobs/{job_id}", status_code=200)
async def get_job_status(
    job_id: int,
    brand=Depends(require_brand),
) -> dict[str, Any]:
    brand_id = _require_brand_id(brand)
    db = get_session_local()()
    try:
        job_repo = CompetitorAnalysisJobRepository(db)
        res_repo = CompetitorAnalysisResultRepository(db)

        job = job_repo.get_for_brand(brand_id, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        results = res_repo.list_by_job(job.id)
        actors = [
            ActorResultOut(
                actor_key=r.actor_key,
                status=r.status,
                summary=r.summary,
                error=r.error,
                started_at=r.started_at,
                finished_at=r.finished_at,
            )
            for r in results
        ]

        payload = JobStatusOut(
            id=job.id,
            status=job.status,
            actors_total=job.actors_total,
            actors_done=job.actors_done,
            actors_failed=job.actors_failed,
            started_at=job.started_at,
            finished_at=job.finished_at,
            actors=actors,
        )
        return {"success": True, "data": payload.model_dump(mode="json")}
    finally:
        db.close()


@router.get("/{competitor_id}/results", status_code=200)
async def get_competitor_results(
    competitor_id: int,
    brand=Depends(require_brand),
) -> dict[str, Any]:
    """Return the latest result row per actor for the competitor.

    Replaces the old "all 6 actors in one envelope" endpoint. Each tab can also
    fetch /results/{actor_key} on demand to load the heavier ``data`` payload.
    """
    brand_id = _require_brand_id(brand)

    db = get_session_local()()
    try:
        comp_repo = CompetitorRepository(db)
        res_repo = CompetitorAnalysisResultRepository(db)
        target_repo = CompetitorTargetRepository(db)
        job_repo = CompetitorAnalysisJobRepository(db)

        competitor = comp_repo.get_for_brand(brand_id, competitor_id)
        if not competitor:
            raise HTTPException(status_code=404, detail="Competitor not found")

        res_repo.heal_stuck_for_competitor(competitor.id)

        # Latest result row per actor — newest wins.
        from app.models.competitor_analysis_result import CompetitorAnalysisResultModel
        latest_per_actor = (
            db.query(CompetitorAnalysisResultModel)
            .filter(
                CompetitorAnalysisResultModel.competitor_id == competitor.id,
                CompetitorAnalysisResultModel.deleted_at.is_(None),
            )
            .order_by(
                CompetitorAnalysisResultModel.actor_key,
                CompetitorAnalysisResultModel.created_at.desc(),
            )
            .all()
        )
        actors_by_key: dict[str, ActorResultOut] = {}
        for row in latest_per_actor:
            if row.actor_key in actors_by_key:
                continue
            actors_by_key[row.actor_key] = ActorResultOut(
                actor_key=row.actor_key,
                status=row.status,
                summary=row.summary,
                error=row.error,
                started_at=row.started_at,
                finished_at=row.finished_at,
            )

        for key in ALL_ACTOR_KEYS:
            actors_by_key.setdefault(
                key, ActorResultOut(actor_key=key, status="idle")
            )

        last_job = job_repo.latest_for_competitor(competitor.id)
        targets = target_repo.list_for_competitor(competitor.id)
        summaries = {k: v.summary for k, v in actors_by_key.items() if v.summary}

        payload = {
            "competitor": _competitor_to_out(
                competitor,
                last_job=last_job,
                targets=targets,
                summaries=summaries or None,
            ).model_dump(mode="json"),
            "job": JobSummary.model_validate(last_job).model_dump(mode="json") if last_job else None,
            "results": {k: v.model_dump(mode="json") for k, v in actors_by_key.items()},
        }
        return {"success": True, "data": payload}
    finally:
        db.close()
