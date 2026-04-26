"""Schedule competitor-analysis jobs onto FastAPI's background-task loop."""
import logging

from fastapi import BackgroundTasks

from app.services.competitor_analysis.orchestrator import run_analysis, run_single_actor


logger = logging.getLogger(__name__)


def enqueue_analysis(
    background_tasks: BackgroundTasks,
    job_id: int,
    competitor_id: int,
    brand_id: int,
    name: str,
) -> None:
    """Schedule ``run_analysis`` to run after the response is sent."""
    logger.info(
        "Enqueueing competitor-analysis job_id=%s brand_id=%s name=%r",
        job_id, brand_id, name,
    )
    background_tasks.add_task(run_analysis, job_id, competitor_id, brand_id, name)


def enqueue_single_actor(
    background_tasks: BackgroundTasks,
    *,
    job_id: int,
    result_id: int,
    competitor_id: int,
    brand_id: int,
    name: str,
    actor_key: str,
) -> None:
    """Schedule ``run_single_actor`` (per-tab retry)."""
    logger.info(
        "Enqueueing single-actor retry actor=%s job_id=%s brand_id=%s",
        actor_key, job_id, brand_id,
    )
    background_tasks.add_task(
        run_single_actor, job_id, result_id, competitor_id, brand_id, name, actor_key,
    )
