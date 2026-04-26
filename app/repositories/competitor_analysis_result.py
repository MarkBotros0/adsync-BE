from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.competitor_analysis_job import (
    JOB_TERMINAL_STATUSES,
    CompetitorAnalysisJobModel,
)
from app.models.competitor_analysis_result import (
    RESULT_STATUS_COMPLETED,
    RESULT_STATUS_FAILED,
    RESULT_STATUS_PENDING,
    RESULT_STATUS_RUNNING,
    CompetitorAnalysisResultModel,
)
from app.repositories.base import BaseRepository


# A scraper that's been "running" longer than this is dead — mark it failed so
# the user can re-run it instead of being blocked by the 409 gate.
STUCK_RESULT_AGE = timedelta(minutes=8)
STUCK_ERROR_MESSAGE = (
    "Run was interrupted (likely a server restart) before it could finish. "
    "Run the scraper again to retry."
)


class CompetitorAnalysisResultRepository(BaseRepository[CompetitorAnalysisResultModel]):
    def __init__(self, db: Session):
        super().__init__(CompetitorAnalysisResultModel, db)

    def list_by_job(self, job_id: int) -> list[CompetitorAnalysisResultModel]:
        return (
            self.db.query(CompetitorAnalysisResultModel)
            .filter(
                CompetitorAnalysisResultModel.job_id == job_id,
                CompetitorAnalysisResultModel.deleted_at.is_(None),
            )
            .order_by(CompetitorAnalysisResultModel.actor_key.asc())
            .all()
        )

    def get_by_job_and_actor(
        self,
        job_id: int,
        actor_key: str,
    ) -> CompetitorAnalysisResultModel | None:
        return (
            self.db.query(CompetitorAnalysisResultModel)
            .filter(
                CompetitorAnalysisResultModel.job_id == job_id,
                CompetitorAnalysisResultModel.actor_key == actor_key,
                CompetitorAnalysisResultModel.deleted_at.is_(None),
            )
            .first()
        )

    def create_pending(
        self,
        job_id: int,
        competitor_id: int,
        brand_id: int,
        actor_key: str,
    ) -> CompetitorAnalysisResultModel:
        result = CompetitorAnalysisResultModel(
            job_id=job_id,
            competitor_id=competitor_id,
            brand_id=brand_id,
            actor_key=actor_key,
        )
        return self.create(result)

    def mark_running(self, result_id: int, apify_run_id: str | None = None) -> None:
        row = self.get(result_id)
        if not row:
            return
        row.status = RESULT_STATUS_RUNNING
        row.started_at = datetime.utcnow()
        row.updated_at = datetime.utcnow()
        if apify_run_id:
            row.apify_run_id = apify_run_id
        self.db.commit()

    def mark_completed(
        self,
        result_id: int,
        data: list | dict,
        summary: dict,
    ) -> None:
        row = self.get(result_id)
        if not row:
            return
        row.status = RESULT_STATUS_COMPLETED
        row.data = data
        row.summary = summary
        row.finished_at = datetime.utcnow()
        row.updated_at = datetime.utcnow()
        self.db.commit()

    def mark_failed(self, result_id: int, error: str) -> None:
        row = self.get(result_id)
        if not row:
            return
        row.status = RESULT_STATUS_FAILED
        row.error = error[:2000]
        row.finished_at = datetime.utcnow()
        row.updated_at = datetime.utcnow()
        self.db.commit()

    def heal_stuck_for_competitor(self, competitor_id: int) -> int:
        """Mark any running/pending result row failed if its parent job is
        already terminal or the row has been "running" longer than the stale
        threshold. Returns the count updated.

        Called inline whenever results are read so a dead worker can't block
        re-runs forever (the 409 gate would otherwise refuse to start a new
        run while a stale row still says running).
        """
        cutoff = datetime.utcnow() - STUCK_RESULT_AGE
        stuck_rows = (
            self.db.query(CompetitorAnalysisResultModel, CompetitorAnalysisJobModel)
            .join(
                CompetitorAnalysisJobModel,
                CompetitorAnalysisJobModel.id == CompetitorAnalysisResultModel.job_id,
            )
            .filter(
                CompetitorAnalysisResultModel.competitor_id == competitor_id,
                CompetitorAnalysisResultModel.deleted_at.is_(None),
                CompetitorAnalysisResultModel.status.in_(
                    [RESULT_STATUS_PENDING, RESULT_STATUS_RUNNING]
                ),
            )
            .all()
        )
        if not stuck_rows:
            return 0
        now = datetime.utcnow()
        updated = 0
        for row, job in stuck_rows:
            job_terminal = job.status in JOB_TERMINAL_STATUSES
            started = row.started_at or row.created_at
            too_old = started is not None and started < cutoff
            if not (job_terminal or too_old):
                continue
            row.status = RESULT_STATUS_FAILED
            row.error = STUCK_ERROR_MESSAGE
            row.finished_at = now
            row.updated_at = now
            updated += 1
        if updated:
            self.db.commit()
        return updated
