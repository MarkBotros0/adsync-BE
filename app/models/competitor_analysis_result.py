from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database import Base


RESULT_STATUS_PENDING = "pending"
RESULT_STATUS_RUNNING = "running"
RESULT_STATUS_COMPLETED = "completed"
RESULT_STATUS_FAILED = "failed"

ACTOR_FACEBOOK_ADS = "facebook_ads"
ACTOR_WEBSITE = "website"
ACTOR_GOOGLE_SEARCH = "google_search"
ACTOR_INSTAGRAM = "instagram"
ACTOR_TIKTOK = "tiktok"
ACTOR_GOOGLE_PLACES = "google_places"

ALL_ACTOR_KEYS = (
    ACTOR_FACEBOOK_ADS,
    ACTOR_WEBSITE,
    ACTOR_GOOGLE_SEARCH,
    ACTOR_INSTAGRAM,
    ACTOR_TIKTOK,
    ACTOR_GOOGLE_PLACES,
)


class CompetitorAnalysisResultModel(Base):
    """Per-actor result row for a single job. Six rows are created per job."""

    __tablename__ = "competitor_analysis_results"
    __table_args__ = (
        UniqueConstraint("job_id", "actor_key", name="uq_results_job_actor"),
    )

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("competitor_analysis_jobs.id"), index=True, nullable=False)
    competitor_id = Column(Integer, ForeignKey("competitors.id"), index=True, nullable=False)
    brand_id = Column(Integer, ForeignKey("brands.id"), index=True, nullable=False)

    actor_key = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default=RESULT_STATUS_PENDING)

    apify_run_id = Column(String, nullable=True)

    data = Column(JSONB, nullable=True)
    summary = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)

    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True, default=None)

    job = relationship("CompetitorAnalysisJobModel", back_populates="results", lazy="select")

    def __repr__(self) -> str:
        return f"<CompetitorAnalysisResult job={self.job_id} actor={self.actor_key} status={self.status}>"
