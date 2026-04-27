"""Single generated report — PDF + CSV bytes stored inline in Postgres."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, LargeBinary, String, Text

from app.database import Base


RUN_STATUS_PENDING = "pending"
RUN_STATUS_GENERATING = "generating"
RUN_STATUS_READY = "ready"
RUN_STATUS_FAILED = "failed"


class ReportRunModel(Base):
    """One produced report instance — either a one-off or a fired ReportSchedule run."""

    __tablename__ = "report_runs"

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), index=True, nullable=False)
    schedule_id = Column(Integer, ForeignKey("report_schedules.id"), nullable=True, index=True)
    triggered_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    status = Column(String, nullable=False, default=RUN_STATUS_PENDING)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    pdf_bytes = Column(LargeBinary, nullable=True)
    csv_bytes = Column(LargeBinary, nullable=True)
    error_message = Column(Text, nullable=True)

    generated_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)  # set after the email send succeeds

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True, default=None)
