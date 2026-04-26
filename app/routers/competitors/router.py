"""Competitor Analysis HTTP router."""
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.database import get_session_local
from app.dependencies import require_brand
from app.models.competitor_analysis_job import JOB_ACTIVE_STATUSES
from app.models.competitor_analysis_result import ALL_ACTOR_KEYS
from app.repositories.competitor import CompetitorRepository, normalize_slug
from app.repositories.competitor_analysis_job import CompetitorAnalysisJobRepository
from app.repositories.competitor_analysis_result import (
    CompetitorAnalysisResultRepository,
)
from app.routers.competitors.schemas import (
    ActorResultOut,
    CompetitorCreateRequest,
    CompetitorOut,
    CompetitorResultsOut,
    JobCreatedOut,
    JobStatusOut,
    JobSummary,
)
from app.services.competitor_analysis.scheduler import enqueue_analysis, enqueue_single_actor


router = APIRouter(prefix="/competitors", tags=["Competitor Analysis"])
logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _competitor_to_out(
    competitor,
    last_job=None,
    summaries: dict[str, dict[str, Any]] | None = None,
) -> CompetitorOut:
    return CompetitorOut(
        id=competitor.id,
        name=competitor.name,
        slug=competitor.slug,
        created_at=competitor.created_at,
        updated_at=competitor.updated_at,
        last_job=JobSummary.model_validate(last_job) if last_job else None,
        summaries=summaries,
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
    if not brand or not getattr(brand, "id", None):
        raise HTTPException(status_code=403, detail="Brand context required")

    db = get_session_local()()
    try:
        comp_repo = CompetitorRepository(db)
        job_repo = CompetitorAnalysisJobRepository(db)
        res_repo = CompetitorAnalysisResultRepository(db)

        competitors = comp_repo.list_by_brand(brand.id)
        out: list[CompetitorOut] = []
        for comp in competitors:
            last_job = job_repo.latest_for_competitor(comp.id)
            summaries: dict[str, dict[str, Any]] | None = None
            if last_job:
                results = res_repo.list_by_job(last_job.id)
                summaries = _build_summaries(results) or None
            out.append(_competitor_to_out(comp, last_job=last_job, summaries=summaries))

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
    background_tasks: BackgroundTasks,
    brand=Depends(require_brand),
) -> dict[str, Any]:
    if not brand or not getattr(brand, "id", None):
        raise HTTPException(status_code=403, detail="Brand context required")

    db = get_session_local()()
    try:
        comp_repo = CompetitorRepository(db)
        slug = normalize_slug(payload.name)
        if not slug:
            raise HTTPException(status_code=422, detail="Name must contain at least one alphanumeric character")

        existing = comp_repo.find_by_slug(brand.id, slug)
        if existing:
            raise HTTPException(status_code=409, detail="Competitor with this name already exists")

        competitor = comp_repo.create_for_brand(brand.id, payload.name)

        # Auto-kick off the first analysis run.
        job_repo = CompetitorAnalysisJobRepository(db)
        job = job_repo.create_pending(
            brand_id=brand.id,
            competitor_id=competitor.id,
            actors_total=len(ALL_ACTOR_KEYS),
        )

        # Read all needed attributes while the session is still open;
        # build the response payload here so we can safely close the session
        # before kicking off the background task.
        competitor_id = competitor.id
        job_id = job.id
        competitor_payload = _competitor_to_out(
            competitor,
            last_job=job,
            summaries=None,
        ).model_dump(mode="json")
    finally:
        db.close()

    enqueue_analysis(
        background_tasks=background_tasks,
        job_id=job_id,
        competitor_id=competitor_id,
        brand_id=brand.id,
        name=payload.name,
    )

    return {
        "success": True,
        "data": {
            "competitor": competitor_payload,
            "job_id": job_id,
        },
    }


@router.get("/{competitor_id}", status_code=200)
async def get_competitor(
    competitor_id: int,
    brand=Depends(require_brand),
) -> dict[str, Any]:
    if not brand or not getattr(brand, "id", None):
        raise HTTPException(status_code=403, detail="Brand context required")

    db = get_session_local()()
    try:
        comp_repo = CompetitorRepository(db)
        job_repo = CompetitorAnalysisJobRepository(db)
        res_repo = CompetitorAnalysisResultRepository(db)

        competitor = comp_repo.get_for_brand(brand.id, competitor_id)
        if not competitor:
            raise HTTPException(status_code=404, detail="Competitor not found")

        last_job = job_repo.latest_for_competitor(competitor.id)
        summaries = None
        if last_job:
            summaries = _build_summaries(res_repo.list_by_job(last_job.id)) or None

        return {
            "success": True,
            "data": _competitor_to_out(
                competitor, last_job=last_job, summaries=summaries
            ).model_dump(mode="json"),
        }
    finally:
        db.close()


@router.delete("/{competitor_id}", status_code=200)
async def delete_competitor(
    competitor_id: int,
    brand=Depends(require_brand),
) -> dict[str, Any]:
    if not brand or not getattr(brand, "id", None):
        raise HTTPException(status_code=403, detail="Brand context required")

    db = get_session_local()()
    try:
        ok = CompetitorRepository(db).soft_delete_for_brand(brand.id, competitor_id)
    finally:
        db.close()

    if not ok:
        raise HTTPException(status_code=404, detail="Competitor not found")
    return {"success": True, "message": "Competitor deleted"}


# ── Refresh + job status + results ────────────────────────────────────────────

@router.post("/{competitor_id}/refresh", status_code=202)
async def refresh_competitor(
    competitor_id: int,
    background_tasks: BackgroundTasks,
    brand=Depends(require_brand),
) -> dict[str, Any]:
    if not brand or not getattr(brand, "id", None):
        raise HTTPException(status_code=403, detail="Brand context required")

    db = get_session_local()()
    try:
        comp_repo = CompetitorRepository(db)
        job_repo = CompetitorAnalysisJobRepository(db)

        competitor = comp_repo.get_for_brand(brand.id, competitor_id)
        if not competitor:
            raise HTTPException(status_code=404, detail="Competitor not found")

        latest = job_repo.latest_for_competitor(competitor.id)
        if latest and latest.status in JOB_ACTIVE_STATUSES:
            raise HTTPException(
                status_code=409,
                detail="A scrape is already running for this competitor",
            )

        job = job_repo.create_pending(
            brand_id=brand.id,
            competitor_id=competitor.id,
            actors_total=len(ALL_ACTOR_KEYS),
        )
        # Snapshot attributes before closing the session.
        name = competitor.name
        job_id = job.id
        job_status = job.status
    finally:
        db.close()

    enqueue_analysis(
        background_tasks=background_tasks,
        job_id=job_id,
        competitor_id=competitor_id,
        brand_id=brand.id,
        name=name,
    )

    return {
        "success": True,
        "data": JobCreatedOut(job_id=job_id, status=job_status).model_dump(),
    }


@router.post("/{competitor_id}/results/{actor_key}/retry", status_code=202)
async def retry_actor(
    competitor_id: int,
    actor_key: str,
    background_tasks: BackgroundTasks,
    brand=Depends(require_brand),
) -> dict[str, Any]:
    """Re-run a single actor inside the most recent job for this competitor.

    Used by the per-tab Retry button. The existing result row is reset to
    pending and re-populated when the actor finishes.
    """
    if not brand or not getattr(brand, "id", None):
        raise HTTPException(status_code=403, detail="Brand context required")

    if actor_key not in ALL_ACTOR_KEYS:
        raise HTTPException(status_code=422, detail=f"Unknown actor key: {actor_key}")

    db = get_session_local()()
    try:
        comp_repo = CompetitorRepository(db)
        job_repo = CompetitorAnalysisJobRepository(db)
        res_repo = CompetitorAnalysisResultRepository(db)

        competitor = comp_repo.get_for_brand(brand.id, competitor_id)
        if not competitor:
            raise HTTPException(status_code=404, detail="Competitor not found")

        job = job_repo.latest_for_competitor(competitor.id)
        if not job:
            raise HTTPException(
                status_code=400,
                detail="No previous scrape to retry. Click Refresh to start one.",
            )

        result = res_repo.get_by_job_and_actor(job.id, actor_key)
        if not result:
            raise HTTPException(status_code=404, detail="Result row not found for this actor")
        if result.status == "running":
            raise HTTPException(status_code=409, detail="This actor is already running")

        # Snapshot what we need before mutating + closing the session.
        job_id = job.id
        result_id = result.id
        previous_status = result.status
        name = competitor.name

        # Reset the result row and adjust the job counters / status.
        result.status = "pending"
        result.data = None
        result.summary = None
        result.error = None
        result.started_at = None
        result.finished_at = None
        from datetime import datetime
        result.updated_at = datetime.utcnow()
        db.commit()

        job_repo.reset_for_actor_retry(job_id, previous_status)
    finally:
        db.close()

    enqueue_single_actor(
        background_tasks,
        job_id=job_id,
        result_id=result_id,
        competitor_id=competitor_id,
        brand_id=brand.id,
        name=name,
        actor_key=actor_key,
    )

    return {
        "success": True,
        "data": {"job_id": job_id, "actor_key": actor_key, "status": "pending"},
    }


@router.get("/jobs/{job_id}", status_code=200)
async def get_job_status(
    job_id: int,
    brand=Depends(require_brand),
) -> dict[str, Any]:
    if not brand or not getattr(brand, "id", None):
        raise HTTPException(status_code=403, detail="Brand context required")

    db = get_session_local()()
    try:
        job_repo = CompetitorAnalysisJobRepository(db)
        res_repo = CompetitorAnalysisResultRepository(db)

        job = job_repo.get_for_brand(brand.id, job_id)
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
    """Return the latest *completed-or-partial* job's per-actor results in full."""
    if not brand or not getattr(brand, "id", None):
        raise HTTPException(status_code=403, detail="Brand context required")

    db = get_session_local()()
    try:
        comp_repo = CompetitorRepository(db)
        job_repo = CompetitorAnalysisJobRepository(db)
        res_repo = CompetitorAnalysisResultRepository(db)

        competitor = comp_repo.get_for_brand(brand.id, competitor_id)
        if not competitor:
            raise HTTPException(status_code=404, detail="Competitor not found")

        # Prefer the most recent job (running/completed/partial/failed) so the UI
        # can show pending tabs while a job is in flight.
        job = job_repo.latest_for_competitor(competitor.id)

        results: list = []
        if job:
            results = res_repo.list_by_job(job.id)

        actors_by_key: dict[str, ActorResultOut] = {}
        for r in results:
            actors_by_key[r.actor_key] = ActorResultOut(
                actor_key=r.actor_key,
                status=r.status,
                summary=r.summary,
                data=r.data,
                error=r.error,
                started_at=r.started_at,
                finished_at=r.finished_at,
            )

        # Fill in any missing actor keys as pending (no job yet).
        for key in ALL_ACTOR_KEYS:
            actors_by_key.setdefault(
                key, ActorResultOut(actor_key=key, status="pending")
            )

        payload = CompetitorResultsOut(
            competitor=_competitor_to_out(
                competitor,
                last_job=job,
                summaries={k: v.summary for k, v in actors_by_key.items() if v.summary},
            ),
            job=JobSummary.model_validate(job) if job else None,
            results=actors_by_key,
        )

        return {"success": True, "data": payload.model_dump(mode="json")}
    finally:
        db.close()
