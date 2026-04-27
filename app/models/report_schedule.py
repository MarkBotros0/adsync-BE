"""Recurring report schedule — drives the in-process scheduled-report runner."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


CADENCE_WEEKLY = "weekly"
CADENCE_MONTHLY = "monthly"
ALL_CADENCES = (CADENCE_WEEKLY, CADENCE_MONTHLY)


class ReportScheduleModel(Base):
    """A user-defined recurring report. The runner builds a PDF and emails recipients.

    ``template_json`` is the section toggles + window choice the user picked when
    creating the schedule (``{"window_days": 30, "sections": ["overview", "audience",
    "ads", "top_posts"]}``).
    """

    __tablename__ = "report_schedules"

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), index=True, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    name = Column(String, nullable=False)
    cadence = Column(String, nullable=False, default=CADENCE_WEEKLY)
    recipients_csv = Column(Text, nullable=False)  # comma-separated email list

    template_json = Column(JSONB, nullable=False, default=dict)

    last_sent_at = Column(DateTime, nullable=True)
    next_sent_at = Column(DateTime, nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True, default=None)
