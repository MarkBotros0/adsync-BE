"""TikTok Ads endpoints — brand-JWT authenticated.

Currently the codebase has zero TikTok ad coverage; this router introduces it. Mirrors
``app/routers/facebook/ads.py``: discovery (advertisers, campaigns) and reporting at
account / campaign / ad level. Returns rows in the unified shape produced by
``normalise_tiktok_row`` so the FE table can stack TikTok and FB data side-by-side.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import get_settings
from app.database import get_session_local
from app.dependencies import require_brand
from app.repositories.tiktok_session import TikTokSessionRepository
from app.services.insights.period_compare import compare_periods, parse_window
from app.services.tiktok.ads import TikTokAdsService, normalise_tiktok_row

router = APIRouter(prefix="/tiktok/ads", tags=["TikTok Ads"])
logger = logging.getLogger(__name__)
settings = get_settings()


def _resolve_token(brand_id: int) -> str:
    db = get_session_local()()
    try:
        sess = TikTokSessionRepository(db).get_by_brand_id(brand_id)
        if not sess:
            raise HTTPException(status_code=404, detail="TikTok not connected for this brand")
        return sess.access_token
    finally:
        db.close()


def _service(brand_id: int) -> TikTokAdsService:
    return TikTokAdsService(access_token=_resolve_token(brand_id))


# ── Discovery ───────────────────────────────────────────────────────────────

@router.get("/advertisers")
async def list_advertisers(brand=Depends(require_brand)) -> dict[str, Any]:
    """List advertiser accounts the brand's TikTok user can access."""
    app_id = getattr(settings, "tiktok_app_id", None) or getattr(settings, "tiktok_client_key", None)
    secret = getattr(settings, "tiktok_app_secret", None) or getattr(settings, "tiktok_client_secret", None)
    if not app_id or not secret:
        raise HTTPException(status_code=501, detail="TikTok marketing-app credentials not configured")
    advertisers = await _service(brand.id).list_advertisers(app_id, secret)
    return {"success": True, "data": advertisers}


@router.get("/{advertiser_id}/campaigns")
async def list_campaigns(advertiser_id: str, brand=Depends(require_brand)) -> dict[str, Any]:
    rows = await _service(brand.id).list_campaigns(advertiser_id)
    return {"success": True, "data": rows}


@router.get("/{advertiser_id}/ads")
async def list_ads(advertiser_id: str, brand=Depends(require_brand)) -> dict[str, Any]:
    rows = await _service(brand.id).list_ads(advertiser_id)
    return {"success": True, "data": rows}


# ── Reporting ───────────────────────────────────────────────────────────────

@router.get("/{advertiser_id}/insights/summary")
async def get_account_summary(
    advertiser_id: str,
    brand=Depends(require_brand),
    since: str | None = Query(None),
    until: str | None = Query(None),
    compare: bool = Query(True),
) -> dict[str, Any]:
    """Account-level KPI tiles. With ``compare=true`` returns a period-over-period diff."""
    win_since, win_until = parse_window(since, until)
    svc = _service(brand.id)

    async def _fetch(s, u):
        rows = await svc.fetch_report(
            advertiser_id,
            start_date=s.isoformat(),
            end_date=u.isoformat(),
            level="AUCTION_ADVERTISER",
            data_level="AUCTION_ADVERTISER",
        )
        normalised = [normalise_tiktok_row(r) for r in rows]
        if not normalised:
            return {}
        # Sum to a single account-level totals object — same shape as FB aggregate.
        spend = sum(n["spend"] for n in normalised)
        impressions = sum(n["impressions"] for n in normalised)
        reach = sum(n["reach"] for n in normalised)
        clicks = sum(n["clicks"] for n in normalised)
        purchases = sum(n["purchases"] for n in normalised)
        return {
            "spend": round(spend, 2),
            "impressions": impressions,
            "reach": reach,
            "clicks": clicks,
            "purchases": purchases,
            "ctr": round((clicks / impressions) * 100, 4) if impressions else 0.0,
            "cpc": round(spend / clicks, 4) if clicks else 0.0,
            "cpm": round((spend / impressions) * 1000, 4) if impressions else 0.0,
            "frequency": round(impressions / reach, 2) if reach else 0.0,
            "cost_per_purchase": round(spend / purchases, 2) if purchases else None,
        }

    if compare:
        comparison = await compare_periods(
            _fetch, win_since, win_until,
            aggregator=lambda totals: float((totals or {}).get("spend") or 0),
        )
        return {"success": True, "data": comparison}

    return {
        "success": True,
        "data": {
            "advertiser_id": advertiser_id,
            "period": {"since": win_since.isoformat(), "until": win_until.isoformat()},
            "totals": await _fetch(win_since, win_until),
        },
    }


@router.get("/{advertiser_id}/insights/by-campaign")
async def get_by_campaign(
    advertiser_id: str,
    brand=Depends(require_brand),
    since: str | None = Query(None),
    until: str | None = Query(None),
) -> dict[str, Any]:
    win_since, win_until = parse_window(since, until)
    svc = _service(brand.id)
    rows = await svc.fetch_report(
        advertiser_id,
        start_date=win_since.isoformat(),
        end_date=win_until.isoformat(),
        level="AUCTION_CAMPAIGN",
        data_level="AUCTION_CAMPAIGN",
    )
    return {"success": True, "data": {
        "advertiser_id": advertiser_id,
        "rows": [normalise_tiktok_row(r) for r in rows],
    }}


@router.get("/{advertiser_id}/insights/by-ad")
async def get_by_ad(
    advertiser_id: str,
    brand=Depends(require_brand),
    since: str | None = Query(None),
    until: str | None = Query(None),
) -> dict[str, Any]:
    win_since, win_until = parse_window(since, until)
    svc = _service(brand.id)
    rows = await svc.fetch_report(
        advertiser_id,
        start_date=win_since.isoformat(),
        end_date=win_until.isoformat(),
        level="AUCTION_AD",
        data_level="AUCTION_AD",
    )
    return {"success": True, "data": {
        "advertiser_id": advertiser_id,
        "rows": [normalise_tiktok_row(r) for r in rows],
    }}
