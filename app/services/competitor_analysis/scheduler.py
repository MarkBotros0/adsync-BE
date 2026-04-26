"""Schedule competitor-analysis runs onto FastAPI's background-task loop."""
import logging

from fastapi import BackgroundTasks

from app.services.competitor_analysis.orchestrator import run_target


logger = logging.getLogger(__name__)


def enqueue_target_run(
    background_tasks: BackgroundTasks,
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
    """Schedule a single-actor scrape to run after the response is sent."""
    logger.info(
        "Enqueueing target run actor=%s job_id=%s brand_id=%s competitor_id=%s",
        actor_key, job_id, brand_id, competitor_id,
    )
    background_tasks.add_task(
        run_target,
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
