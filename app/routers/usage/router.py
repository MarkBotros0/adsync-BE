"""Brand-level Apify usage and ledger endpoints."""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.database import get_session_local
from app.dependencies import require_brand
from app.repositories.apify_run import ApifyRunRepository
from app.routers.competitors.schemas import ApifyRunOut, BrandUsageOut, BudgetSnapshot
from app.services.budget import check_budget


router = APIRouter(prefix="/usage", tags=["Usage"])
logger = logging.getLogger(__name__)


def _require_brand_id(brand) -> int:
    if not brand or not getattr(brand, "id", None):
        raise HTTPException(status_code=403, detail="Brand context required")
    return int(brand.id)


@router.get("/brand/current", status_code=200)
async def current_brand_usage(brand=Depends(require_brand)) -> dict[str, Any]:
    brand_id = _require_brand_id(brand)
    org_id = getattr(brand, "organization_id", None)

    db = get_session_local()()
    try:
        usage = ApifyRunRepository(db).monthly_usage_for_brand(brand_id)
    finally:
        db.close()

    budget = check_budget(brand_id, org_id)
    payload = BrandUsageOut(
        period_start=usage["period_start"],
        compute_units_used=float(usage["compute_units"]),
        usage_usd=float(usage["usage_usd"]),
        runs=int(usage["runs"]),
        by_actor=usage["by_actor"],
        budget=BudgetSnapshot(
            used_compute_units=budget.used_compute_units,
            used_usd=budget.used_usd,
            monthly_compute_unit_budget=budget.monthly_compute_unit_budget,
            warn_at_pct=budget.warn_at_pct,
            percent_used=budget.percent_used,
            will_warn=budget.will_warn,
            will_block=budget.will_block,
            period_start=budget.period_start,
        ),
    )
    return {"success": True, "data": payload.model_dump(mode="json")}


@router.get("/brand/runs", status_code=200)
async def list_runs(
    limit: int = 50,
    cursor: int | None = None,
    brand=Depends(require_brand),
) -> dict[str, Any]:
    brand_id = _require_brand_id(brand)
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 200")

    db = get_session_local()()
    try:
        rows = ApifyRunRepository(db).list_for_brand(
            brand_id, limit=limit, before_id=cursor,
        )
    finally:
        db.close()

    items = [ApifyRunOut.model_validate(r).model_dump(mode="json") for r in rows]
    next_cursor = rows[-1].id if rows and len(rows) == limit else None
    return {
        "success": True,
        "data": {
            "items": items,
            "next_cursor": next_cursor,
            "limit": limit,
        },
    }
