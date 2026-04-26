from datetime import datetime

from sqlalchemy.orm import Session

from app.models.competitor_analysis_job import (
    JOB_ACTIVE_STATUSES,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    JOB_STATUS_PARTIAL,
    JOB_STATUS_RUNNING,
    CompetitorAnalysisJobModel,
)
from app.repositories.base import BaseRepository


class CompetitorAnalysisJobRepository(BaseRepository[CompetitorAnalysisJobModel]):
    def __init__(self, db: Session):
        super().__init__(CompetitorAnalysisJobModel, db)

    def get_for_brand(self, brand_id: int, job_id: int) -> CompetitorAnalysisJobModel | None:
        return (
            self.db.query(CompetitorAnalysisJobModel)
            .filter(
                CompetitorAnalysisJobModel.id == job_id,
                CompetitorAnalysisJobModel.brand_id == brand_id,
                CompetitorAnalysisJobModel.deleted_at.is_(None),
            )
            .first()
        )

    def latest_for_competitor(self, competitor_id: int) -> CompetitorAnalysisJobModel | None:
        return (
            self.db.query(CompetitorAnalysisJobModel)
            .filter(
                CompetitorAnalysisJobModel.competitor_id == competitor_id,
                CompetitorAnalysisJobModel.deleted_at.is_(None),
            )
            .order_by(CompetitorAnalysisJobModel.created_at.desc())
            .first()
        )

    def latest_completed_for_competitor(self, competitor_id: int) -> CompetitorAnalysisJobModel | None:
        return (
            self.db.query(CompetitorAnalysisJobModel)
            .filter(
                CompetitorAnalysisJobModel.competitor_id == competitor_id,
                CompetitorAnalysisJobModel.status.in_(
                    [JOB_STATUS_COMPLETED, JOB_STATUS_PARTIAL]
                ),
                CompetitorAnalysisJobModel.deleted_at.is_(None),
            )
            .order_by(CompetitorAnalysisJobModel.created_at.desc())
            .first()
        )

    def has_active_job(self, competitor_id: int) -> bool:
        latest = self.latest_for_competitor(competitor_id)
        return bool(latest and latest.status in JOB_ACTIVE_STATUSES)

    def create_pending(
        self,
        brand_id: int,
        competitor_id: int,
        actors_total: int,
    ) -> CompetitorAnalysisJobModel:
        job = CompetitorAnalysisJobModel(
            brand_id=brand_id,
            competitor_id=competitor_id,
            actors_total=actors_total,
        )
        return self.create(job)

    def mark_running(self, job_id: int) -> None:
        job = self.get(job_id)
        if not job:
            return
        job.status = JOB_STATUS_RUNNING
        job.started_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        self.db.commit()

    def increment_done(self, job_id: int) -> None:
        job = self.get(job_id)
        if not job:
            return
        job.actors_done = (job.actors_done or 0) + 1
        job.updated_at = datetime.utcnow()
        self.db.commit()

    def increment_failed(self, job_id: int) -> None:
        job = self.get(job_id)
        if not job:
            return
        job.actors_failed = (job.actors_failed or 0) + 1
        job.updated_at = datetime.utcnow()
        self.db.commit()

    def finalize(self, job_id: int) -> None:
        """Set the final status (completed / partial / failed) based on counters."""
        job = self.get(job_id)
        if not job:
            return
        total = job.actors_total or 0
        done = job.actors_done or 0
        failed = job.actors_failed or 0
        if total > 0 and done == total and failed == 0:
            job.status = JOB_STATUS_COMPLETED
        elif done == 0:
            job.status = JOB_STATUS_FAILED
        else:
            job.status = JOB_STATUS_PARTIAL
        job.finished_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        self.db.commit()

    def mark_failed(self, job_id: int, error_message: str) -> None:
        job = self.get(job_id)
        if not job:
            return
        job.status = JOB_STATUS_FAILED
        job.error_message = error_message[:2000]
        job.finished_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        self.db.commit()

    def reset_for_actor_retry(
        self,
        job_id: int,
        previous_actor_status: str,
    ) -> None:
        """Adjust counters and status when retrying a single actor in an existing job."""
        job = self.get(job_id)
        if not job:
            return
        if previous_actor_status == "completed" and (job.actors_done or 0) > 0:
            job.actors_done = (job.actors_done or 0) - 1
        elif previous_actor_status == "failed" and (job.actors_failed or 0) > 0:
            job.actors_failed = (job.actors_failed or 0) - 1
        job.status = JOB_STATUS_RUNNING
        job.finished_at = None
        if not job.started_at:
            job.started_at = datetime.utcnow()
        job.error_message = None
        job.updated_at = datetime.utcnow()
        self.db.commit()
