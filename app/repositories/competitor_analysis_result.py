from datetime import datetime

from sqlalchemy.orm import Session

from app.models.competitor_analysis_result import (
    RESULT_STATUS_COMPLETED,
    RESULT_STATUS_FAILED,
    RESULT_STATUS_RUNNING,
    CompetitorAnalysisResultModel,
)
from app.repositories.base import BaseRepository


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
