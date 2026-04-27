"""Unified Ads feed — stacks Facebook + TikTok ad rows in a single call.

Mirrors ``app/routers/content/feed.py`` for the ads world. The FE makes one
authenticated call and gets back per-platform totals plus a flat list of normalised
rows (the FB and TikTok normalisers produce the same columns).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_session_local
from app.dependencies import require_brand
from app.repositories.facebook_session import FacebookSessionRepository
from app.repositories.tiktok_session import TikTokSessionRepository
from app.services.facebook.ads import AdsService as FacebookAdsService
from app.services.facebook.ads import aggregate_totals, normalise_insights_row
from app.services.insights.period_compare import parse_window
from app.services.tiktok.ads import TikTokAdsService, normalise_tiktok_row

router = APIRouter(prefix="/ads", tags=["Ads"])
logger = logging.getLogger(__name__)


def _normalise_act(account_id: str) -> str:
    return account_id if account_id.startswith("act_") else f"act_{account_id}"


async def _facebook_rows(
    brand_id: int, since: str, until: str, fb_account_id: str | None
) -> list[dict[str, Any]]:
    """Fetch + normalise the FB account's insights for the window. Returns [] on no session."""
    db = get_session_local()()
    try:
        sess = FacebookSessionRepository(db).get_by_brand_id(brand_id)
        if not sess:
            return []
        token = sess.access_token
    finally:
        db.close()

    svc = FacebookAdsService(access_token=token)
    if not fb_account_id:
        # Pick the first account the token can see — same convention as the page picker.
        accounts = (await svc.fetch_ad_accounts()).get("data", [])
        if not accounts:
            return []
        fb_account_id = accounts[0].get("account_id") or accounts[0].get("id")

    raw = await svc.fetch_account_insights(
        _normalise_act(fb_account_id), since=since, until=until
    )
    rows = [normalise_insights_row(r) for r in raw.get("data", [])]
    for r in rows:
        r["platform"] = "facebook"
    return rows


async def _tiktok_rows(
    brand_id: int, since: str, until: str, tiktok_advertiser_id: str | None
) -> list[dict[str, Any]]:
    """Fetch + normalise the TikTok advertiser's report for the window."""
    if not tiktok_advertiser_id:
        # No way to auto-discover advertisers without partner credentials, so we just
        # skip if the FE didn't pass an explicit advertiser_id.
        return []
    db = get_session_local()()
    try:
        sess = TikTokSessionRepository(db).get_by_brand_id(brand_id)
        if not sess:
            return []
        token = sess.access_token
    finally:
        db.close()

    svc = TikTokAdsService(access_token=token)
    rows_raw = await svc.fetch_report(
        tiktok_advertiser_id,
        start_date=since,
        end_date=until,
        level="AUCTION_ADVERTISER",
        data_level="AUCTION_ADVERTISER",
    )
    return [normalise_tiktok_row(r) for r in rows_raw]


@router.get("/feed")
async def get_ads_feed(
    brand=Depends(require_brand),
    since: str | None = Query(None),
    until: str | None = Query(None),
    platforms: str | None = Query(None, description="Comma-separated: facebook,tiktok"),
    fb_account_id: str | None = Query(None, description="Optional explicit FB ad account id"),
    tiktok_advertiser_id: str | None = Query(None, description="Required for TikTok rows"),
) -> dict[str, Any]:
    """Combined ads feed across all connected ad platforms.

    Each row is the unified KPI shape: spend / impressions / reach / clicks / CTR / CPM /
    CPC / purchases / ROAS / video p25-p100 etc. Aggregates included so the FE doesn't
    have to recompute them.
    """
    win_since, win_until = parse_window(since, until)
    plat_filter: set[str] | None = (
        {p.strip().lower() for p in platforms.split(",") if p.strip()} if platforms else None
    )

    def _want(p: str) -> bool:
        return plat_filter is None or p in plat_filter

    fb_task = (
        _facebook_rows(brand.id, win_since.isoformat(), win_until.isoformat(), fb_account_id)
        if _want("facebook") else asyncio.sleep(0, result=[])
    )
    tt_task = (
        _tiktok_rows(brand.id, win_since.isoformat(), win_until.isoformat(), tiktok_advertiser_id)
        if _want("tiktok") else asyncio.sleep(0, result=[])
    )

    fb_rows, tt_rows = await asyncio.gather(fb_task, tt_task, return_exceptions=False)

    rows = [*fb_rows, *tt_rows]
    per_platform = {
        "facebook": aggregate_totals(fb_rows) if fb_rows else {},
        "tiktok": _aggregate_tiktok(tt_rows) if tt_rows else {},
    }

    return {
        "success": True,
        "data": {
            "period": {"since": win_since.isoformat(), "until": win_until.isoformat()},
            "platforms_fetched": [p for p, t in per_platform.items() if t],
            "rows": rows,
            "totals_by_platform": per_platform,
            "totals": _aggregate_unified(rows),
        },
    }


def _aggregate_tiktok(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Roll up a list of normalised TikTok rows into account totals (rates recomputed)."""
    if not rows:
        return {}
    spend = sum(r["spend"] for r in rows)
    impressions = sum(r["impressions"] for r in rows)
    reach = sum(r["reach"] for r in rows)
    clicks = sum(r["clicks"] for r in rows)
    purchases = sum(r["purchases"] for r in rows)
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


def _aggregate_unified(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Cross-platform totals — same KPI columns regardless of platform."""
    if not rows:
        return {}
    spend = sum(r.get("spend") or 0 for r in rows)
    impressions = sum(r.get("impressions") or 0 for r in rows)
    reach = sum(r.get("reach") or 0 for r in rows)
    clicks = sum(r.get("clicks") or 0 for r in rows)
    purchases = sum(r.get("purchases") or 0 for r in rows)
    purchase_value = sum(r.get("purchase_value") or 0 for r in rows)
    return {
        "spend": round(spend, 2),
        "impressions": impressions,
        "reach": reach,
        "clicks": clicks,
        "purchases": purchases,
        "purchase_value": round(purchase_value, 2),
        "ctr": round((clicks / impressions) * 100, 4) if impressions else 0.0,
        "cpc": round(spend / clicks, 4) if clicks else 0.0,
        "cpm": round((spend / impressions) * 1000, 4) if impressions else 0.0,
        "frequency": round(impressions / reach, 2) if reach else 0.0,
        "roas": round(purchase_value / spend, 2) if spend else None,
        "cost_per_purchase": round(spend / purchases, 2) if purchases else None,
    }
