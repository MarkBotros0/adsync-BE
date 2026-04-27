"""Reports endpoints — one-off generate, recurring schedules, PDF download."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.database import get_session_local
from app.dependencies import require_brand
from app.models.report_run import (
    RUN_STATUS_FAILED,
    RUN_STATUS_GENERATING,
    RUN_STATUS_READY,
    ReportRunModel,
)
from app.models.report_schedule import ALL_CADENCES, CADENCE_WEEKLY, ReportScheduleModel
from app.services.reports.builder import build_pdf

router = APIRouter(prefix="/reports", tags=["Reports"])
logger = logging.getLogger(__name__)


# ── Schemas ─────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    period_start: datetime
    period_end: datetime
    sections: list[str] = Field(default_factory=lambda: ["overview"])
    kpis: dict[str, Any] | None = None


class ScheduleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    cadence: str = Field(CADENCE_WEEKLY)
    recipients: list[EmailStr]
    template: dict[str, Any] = Field(default_factory=dict)


class ScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    brand_id: int
    name: str
    cadence: str
    recipients_csv: str
    template_json: dict[str, Any]
    last_sent_at: datetime | None = None
    next_sent_at: datetime


class RunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    brand_id: int
    schedule_id: int | None = None
    status: str
    period_start: datetime
    period_end: datetime
    generated_at: datetime | None = None
    delivered_at: datetime | None = None
    error_message: str | None = None


# ── One-off generate ────────────────────────────────────────────────────────

@router.post("/generate", response_model=RunSummary, status_code=status.HTTP_201_CREATED)
async def generate_one_off(
    payload: GenerateRequest,
    brand=Depends(require_brand),
) -> Any:
    """Generate a single PDF report on demand. Returns the run row immediately."""
    db = get_session_local()()
    try:
        run = ReportRunModel(
            brand_id=brand.id,
            status=RUN_STATUS_GENERATING,
            period_start=payload.period_start,
            period_end=payload.period_end,
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        try:
            pdf_bytes = await build_pdf(
                db,
                brand_id=brand.id,
                period_start=payload.period_start,
                period_end=payload.period_end,
                sections=payload.sections,
                kpis=payload.kpis,
            )
            run.pdf_bytes = pdf_bytes
            run.status = RUN_STATUS_READY
            run.generated_at = datetime.utcnow()
        except Exception as exc:  # noqa: BLE001
            run.status = RUN_STATUS_FAILED
            run.error_message = str(exc)
            logger.exception("PDF generation failed for brand %d", brand.id)
        db.commit()
        db.refresh(run)
        return run
    finally:
        db.close()


@router.get("/runs", response_model=list[RunSummary])
async def list_runs(brand=Depends(require_brand), limit: int = 50) -> Any:
    """List recent report runs for the brand. PDF bytes excluded — fetch via /raw."""
    db = get_session_local()()
    try:
        return (
            db.query(ReportRunModel)
            .filter(
                ReportRunModel.brand_id == brand.id,
                ReportRunModel.deleted_at.is_(None),
            )
            .order_by(ReportRunModel.created_at.desc())
            .limit(limit)
            .all()
        )
    finally:
        db.close()


@router.get("/runs/{run_id}/pdf")
async def download_pdf(run_id: int, brand=Depends(require_brand)) -> Any:
    """Stream the PDF for a generated run. Brand-JWT scoped."""
    db = get_session_local()()
    try:
        run = (
            db.query(ReportRunModel)
            .filter(
                ReportRunModel.id == run_id,
                ReportRunModel.brand_id == brand.id,
                ReportRunModel.deleted_at.is_(None),
            )
            .first()
        )
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        if run.status != RUN_STATUS_READY or not run.pdf_bytes:
            raise HTTPException(status_code=409, detail=f"Run is not ready (status='{run.status}')")
        pdf = run.pdf_bytes
    finally:
        db.close()

    return StreamingResponse(
        iter([pdf]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report-{run_id}.pdf"'},
    )


# ── Recurring schedules ────────────────────────────────────────────────────

@router.get("/schedules", response_model=list[ScheduleResponse])
async def list_schedules(brand=Depends(require_brand)) -> Any:
    db = get_session_local()()
    try:
        return (
            db.query(ReportScheduleModel)
            .filter(
                ReportScheduleModel.brand_id == brand.id,
                ReportScheduleModel.deleted_at.is_(None),
            )
            .order_by(ReportScheduleModel.created_at.desc())
            .all()
        )
    finally:
        db.close()


@router.post("/schedules", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    payload: ScheduleCreate,
    brand=Depends(require_brand),
) -> Any:
    if payload.cadence not in ALL_CADENCES:
        raise HTTPException(status_code=422, detail=f"cadence must be one of {ALL_CADENCES}")
    if not payload.recipients:
        raise HTTPException(status_code=422, detail="recipients cannot be empty")
    db = get_session_local()()
    try:
        delta = timedelta(weeks=1) if payload.cadence == CADENCE_WEEKLY else timedelta(days=30)
        sched = ReportScheduleModel(
            brand_id=brand.id,
            created_by_user_id=getattr(brand, "owner_user_id", 0),
            name=payload.name,
            cadence=payload.cadence,
            recipients_csv=",".join(payload.recipients),
            template_json=payload.template,
            next_sent_at=datetime.utcnow() + delta,
        )
        db.add(sched)
        db.commit()
        db.refresh(sched)
        return sched
    finally:
        db.close()


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(schedule_id: int, brand=Depends(require_brand)) -> None:
    db = get_session_local()()
    try:
        sched = (
            db.query(ReportScheduleModel)
            .filter(
                ReportScheduleModel.id == schedule_id,
                ReportScheduleModel.brand_id == brand.id,
                ReportScheduleModel.deleted_at.is_(None),
            )
            .first()
        )
        if not sched:
            raise HTTPException(status_code=404, detail="Schedule not found")
        sched.deleted_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()


@router.post("/schedules/{schedule_id}/run-now", response_model=RunSummary)
async def run_schedule_now(
    schedule_id: int,
    brand=Depends(require_brand),
) -> Any:
    """Force a scheduled report to run immediately (uses its template + window)."""
    db = get_session_local()()
    try:
        sched = (
            db.query(ReportScheduleModel)
            .filter(
                ReportScheduleModel.id == schedule_id,
                ReportScheduleModel.brand_id == brand.id,
                ReportScheduleModel.deleted_at.is_(None),
            )
            .first()
        )
        if not sched:
            raise HTTPException(status_code=404, detail="Schedule not found")
        sched.next_sent_at = datetime.utcnow()
        db.commit()
        # The in-process runner will pick it up on its next 30s tick. Return a
        # shell run row so the FE has something to poll on.
        run = ReportRunModel(
            brand_id=brand.id,
            schedule_id=sched.id,
            status="pending",
            period_start=datetime.utcnow() - timedelta(days=int((sched.template_json or {}).get("window_days") or 30)),
            period_end=datetime.utcnow(),
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run
    finally:
        db.close()
