from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, String

from app.database import Base


APIFY_RUN_STATUS_RUNNING = "running"
APIFY_RUN_STATUS_SUCCEEDED = "succeeded"
APIFY_RUN_STATUS_FAILED = "failed"
APIFY_RUN_STATUS_TIMED_OUT = "timed-out"


class ApifyRunModel(Base):
    """Cost/usage ledger — one row per Apify actor run.

    Captures ``stats.computeUnits`` and ``usageTotalUsd`` from the Apify run
    metadata so we can show per-brand spend, enforce budgets, and estimate
    future runs from rolling averages. Decoupled from
    ``competitor_analysis_results`` so the audit trail survives result rewrites
    and per-actor retries.
    """

    __tablename__ = "apify_runs"
    __table_args__ = (
        Index("ix_apify_runs_brand_created", "brand_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), index=True, nullable=False)
    competitor_id = Column(Integer, ForeignKey("competitors.id"), index=True, nullable=True)
    result_id = Column(Integer, ForeignKey("competitor_analysis_results.id"), index=True, nullable=True)

    actor_key = Column(String, nullable=False, index=True)
    apify_run_id = Column(String, nullable=True, index=True)
    status = Column(String, nullable=False, default=APIFY_RUN_STATUS_RUNNING)

    compute_units = Column(Numeric(12, 4), nullable=True)
    usage_total_usd = Column(Numeric(10, 4), nullable=True)
    dataset_id = Column(String, nullable=True)

    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True, default=None)

    def __repr__(self) -> str:
        return f"<ApifyRun brand={self.brand_id} actor={self.actor_key} run={self.apify_run_id} cu={self.compute_units}>"
