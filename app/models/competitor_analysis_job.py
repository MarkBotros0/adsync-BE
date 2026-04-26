from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


JOB_STATUS_PENDING = "pending"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_PARTIAL = "partial"
JOB_STATUS_FAILED = "failed"

JOB_TERMINAL_STATUSES = frozenset({JOB_STATUS_COMPLETED, JOB_STATUS_PARTIAL, JOB_STATUS_FAILED})
JOB_ACTIVE_STATUSES = frozenset({JOB_STATUS_PENDING, JOB_STATUS_RUNNING})


class CompetitorAnalysisJobModel(Base):
    """A single end-to-end scrape run for a competitor (kicks off all 6 actors)."""

    __tablename__ = "competitor_analysis_jobs"

    id = Column(Integer, primary_key=True, index=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id"), index=True, nullable=False)
    brand_id = Column(Integer, ForeignKey("brands.id"), index=True, nullable=False)

    status = Column(String, nullable=False, default=JOB_STATUS_PENDING, index=True)

    actors_total = Column(Integer, nullable=False, default=0)
    actors_done = Column(Integer, nullable=False, default=0)
    actors_failed = Column(Integer, nullable=False, default=0)

    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True, default=None)

    competitor = relationship("CompetitorModel", back_populates="jobs", lazy="select")
    results = relationship(
        "CompetitorAnalysisResultModel",
        back_populates="job",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<CompetitorAnalysisJob {self.id} status={self.status}>"
