"""Facebook Marketing API ad insights — brand-JWT authenticated.

Replaces the old session_id-based stub with the full marketer KPI surface:
account / campaign / ad-level breakdowns, demographics, geo, placement.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_session_local
from app.dependencies import require_brand
from app.repositories.facebook_session import FacebookSessionRepository
from app.services.facebook.ads import AdsService, aggregate_totals, normalise_insights_row
from app.services.insights.period_compare import compare_periods, parse_window

router = APIRouter(prefix="/facebook/ads", tags=["Facebook Ads"])
logger = logging.getLogger(__name__)


def _resolve_user_token(brand_id: int) -> str:
    """Pull the user-level FB access token for the brand. Ad accounts query against this token."""
    db = get_session_local()()
    try:
        fb_session = FacebookSessionRepository(db).get_by_brand_id(brand_id)
        if not fb_session:
            raise HTTPException(status_code=404, detail="Facebook not connected for this brand")
        return fb_session.access_token
    finally:
        db.close()


def _normalise_account_id(account_id: str) -> str:
    """Marketing API requires the ``act_`` prefix; strip-and-readd lets the FE pass either."""
    return account_id if account_id.startswith("act_") else f"act_{account_id}"


# ── Account discovery ───────────────────────────────────────────────────────

@router.get("/accounts")
async def list_ad_accounts(brand=Depends(require_brand)) -> dict[str, Any]:
    """List ad accounts the brand's connected FB user manages — populates the account picker."""
    svc = AdsService(access_token=_resolve_user_token(brand.id))
    raw = await svc.fetch_ad_accounts()
    return {"success": True, "data": raw.get("data", [])}


@router.get("/{account_id}/campaigns")
async def list_campaigns(account_id: str, brand=Depends(require_brand)) -> dict[str, Any]:
    """List campaigns under an ad account — drives the campaign filter on the dashboard."""
    svc = AdsService(access_token=_resolve_user_token(brand.id))
    raw = await svc.fetch_campaigns(_normalise_account_id(account_id))
    return {"success": True, "data": raw.get("data", [])}


# ── KPI summary (with optional period-over-period) ──────────────────────────

@router.get("/{account_id}/insights/summary")
async def get_account_summary(
    account_id: str,
    brand=Depends(require_brand),
    since: str | None = Query(None),
    until: str | None = Query(None),
    compare: bool = Query(True, description="Also fetch the previous equal-length window"),
) -> dict[str, Any]:
    """Account-level KPI tiles for the ads dashboard. Returns totals + delta vs prior period."""
    win_since, win_until = parse_window(since, until)
    acct = _normalise_account_id(account_id)
    svc = AdsService(access_token=_resolve_user_token(brand.id))

    async def _fetch_totals(s, u):
        raw = await svc.fetch_account_insights(acct, since=s.isoformat(), until=u.isoformat())
        rows = [normalise_insights_row(r) for r in raw.get("data", [])]
        return aggregate_totals(rows)

    if compare:
        comparison = await compare_periods(
            _fetch_totals,
            win_since,
            win_until,
            aggregator=lambda totals: float((totals or {}).get("spend") or 0),
        )
        return {"success": True, "data": comparison}

    totals = await _fetch_totals(win_since, win_until)
    return {
        "success": True,
        "data": {
            "account_id": acct,
            "period": {"since": win_since.isoformat(), "until": win_until.isoformat()},
            "totals": totals,
        },
    }


# ── Daily / per-period series ───────────────────────────────────────────────

@router.get("/{account_id}/insights/series")
async def get_account_series(
    account_id: str,
    brand=Depends(require_brand),
    since: str | None = Query(None),
    until: str | None = Query(None),
    granularity: str = Query("1", description="time_increment — '1'=daily, 'monthly', etc."),
) -> dict[str, Any]:
    """Time-series rows for the spend / CPM / ROAS line chart."""
    win_since, win_until = parse_window(since, until)
    acct = _normalise_account_id(account_id)
    svc = AdsService(access_token=_resolve_user_token(brand.id))

    raw = await svc.fetch_account_insights(
        acct,
        since=win_since.isoformat(),
        until=win_until.isoformat(),
        time_increment=granularity,
    )
    rows = [normalise_insights_row(r) for r in raw.get("data", [])]
    return {
        "success": True,
        "data": {
            "account_id": acct,
            "period": {"since": win_since.isoformat(), "until": win_until.isoformat()},
            "series": rows,
        },
    }


# ── Per-campaign + per-ad tables ────────────────────────────────────────────

@router.get("/{account_id}/insights/by-campaign")
async def get_by_campaign(
    account_id: str,
    brand=Depends(require_brand),
    since: str | None = Query(None),
    until: str | None = Query(None),
) -> dict[str, Any]:
    win_since, win_until = parse_window(since, until)
    acct = _normalise_account_id(account_id)
    svc = AdsService(access_token=_resolve_user_token(brand.id))
    raw = await svc.fetch_campaign_insights(acct, since=win_since.isoformat(), until=win_until.isoformat())
    rows = [normalise_insights_row(r) for r in raw.get("data", [])]
    return {"success": True, "data": {"account_id": acct, "rows": rows}}


@router.get("/{account_id}/insights/by-ad")
async def get_by_ad(
    account_id: str,
    brand=Depends(require_brand),
    since: str | None = Query(None),
    until: str | None = Query(None),
) -> dict[str, Any]:
    """Per-ad table — drives the per-creative leaderboard."""
    win_since, win_until = parse_window(since, until)
    acct = _normalise_account_id(account_id)
    svc = AdsService(access_token=_resolve_user_token(brand.id))
    raw = await svc.fetch_ad_insights(acct, since=win_since.isoformat(), until=win_until.isoformat())
    rows = [normalise_insights_row(r) for r in raw.get("data", [])]
    return {"success": True, "data": {"account_id": acct, "rows": rows}}


# ── Breakdowns: demographics / geo / placement ──────────────────────────────

@router.get("/{account_id}/insights/demographics")
async def get_demographics(
    account_id: str,
    brand=Depends(require_brand),
    since: str | None = Query(None),
    until: str | None = Query(None),
) -> dict[str, Any]:
    win_since, win_until = parse_window(since, until)
    acct = _normalise_account_id(account_id)
    svc = AdsService(access_token=_resolve_user_token(brand.id))
    raw = await svc.fetch_account_demographics(acct, since=win_since.isoformat(), until=win_until.isoformat())
    rows = [
        {**normalise_insights_row(r), "age": r.get("age"), "gender": r.get("gender")}
        for r in raw.get("data", [])
    ]
    return {"success": True, "data": {"account_id": acct, "rows": rows}}


@router.get("/{account_id}/insights/geo")
async def get_geo(
    account_id: str,
    brand=Depends(require_brand),
    since: str | None = Query(None),
    until: str | None = Query(None),
) -> dict[str, Any]:
    win_since, win_until = parse_window(since, until)
    acct = _normalise_account_id(account_id)
    svc = AdsService(access_token=_resolve_user_token(brand.id))
    raw = await svc.fetch_account_geo(acct, since=win_since.isoformat(), until=win_until.isoformat())
    rows = [
        {**normalise_insights_row(r), "country": r.get("country")}
        for r in raw.get("data", [])
    ]
    return {"success": True, "data": {"account_id": acct, "rows": rows}}


@router.get("/{account_id}/insights/placement")
async def get_placement(
    account_id: str,
    brand=Depends(require_brand),
    since: str | None = Query(None),
    until: str | None = Query(None),
) -> dict[str, Any]:
    win_since, win_until = parse_window(since, until)
    acct = _normalise_account_id(account_id)
    svc = AdsService(access_token=_resolve_user_token(brand.id))
    raw = await svc.fetch_account_placement(acct, since=win_since.isoformat(), until=win_until.isoformat())
    rows = [
        {
            **normalise_insights_row(r),
            "publisher_platform": r.get("publisher_platform"),
            "platform_position": r.get("platform_position"),
        }
        for r in raw.get("data", [])
    ]
    return {"success": True, "data": {"account_id": acct, "rows": rows}}
