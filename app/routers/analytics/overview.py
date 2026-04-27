"""Analytics Overview endpoint — top-of-page KPIs + Grade distribution + gender/age charts.

Implements the marketing-expert spec exactly:
- Top-of-page row: followers growth %, avg total engagements, avg likes, avg reach,
  avg saves, avg shares (per post in the filtered window).
- Per-post Grade A/B/C/D using the weighted-score formula.
- Gender + age charts (Instagram audience for now — Facebook page-level demographics
  are wired separately in /facebook/insights/page/demographics).

Driven by the existing `/content/feed` data so the same window/filter the user is
already viewing on /content drives the analytics roll-ups — no second source of truth.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_session_local
from app.dependencies import require_brand
from app.repositories.instagram_session import InstagramSessionRepository
from app.services.analytics.derived import (
    aggregate_engagement_rate,
    avg,
    grade_distribution,
    grade_posts,
    interactions_per_1k_followers,
    top_of_page_kpis,
    total_saves,
)
from app.services.insights.period_compare import parse_window
from app.services.instagram.insights import InstagramInsightsService

router = APIRouter(prefix="/analytics", tags=["Analytics Overview"])
logger = logging.getLogger(__name__)


def _ig_session_for(brand_id: int) -> tuple[str, str] | None:
    """Return ``(ig_user_id, access_token)`` for the brand's IG session, or None."""
    db = get_session_local()()
    try:
        sess = InstagramSessionRepository(db).get_by_brand_id(brand_id)
        if not sess:
            return None
        return sess.ig_user_id, sess.access_token
    finally:
        db.close()


def _normalise_post(item: dict[str, Any]) -> dict[str, Any]:
    """Pull likes/comments/shares/saves/reach onto the top level so derived calcs work
    against either a content-feed mention or a raw insights payload."""
    eng = item.get("engagement") or {}
    out = dict(item)
    out.setdefault("likes", eng.get("likes") or item.get("likes") or 0)
    out.setdefault("comments", eng.get("comments") or item.get("comments") or 0)
    out.setdefault("shares", eng.get("shares") or item.get("shares") or 0)
    out.setdefault("saves", eng.get("saved") or eng.get("saves") or item.get("saves") or 0)
    out.setdefault("reach", item.get("reach") or 0)
    return out


@router.post("/overview")
async def analytics_overview(
    posts: list[dict[str, Any]],
    brand=Depends(require_brand),
    follower_count_start: int | None = None,
    follower_count_end: int | None = None,
) -> dict[str, Any]:
    """Compute every marketing-expert KPI from a list of posts.

    POST body is the list of posts the FE is already showing on /content for the
    selected window (the FE has them cached in `ContentDataContext`, so passing them
    in avoids re-fetching from each platform). Server adds the math.
    """
    normalised = [_normalise_post(p) for p in posts]
    grade_posts(normalised)

    total_followers = follower_count_end or follower_count_start or 0
    total_engagements = sum(
        int(p.get("likes") or 0)
        + int(p.get("comments") or 0)
        + int(p.get("shares") or 0)
        + int(p.get("saves") or 0)
        for p in normalised
    )

    return {
        "success": True,
        "data": {
            "top_of_page": top_of_page_kpis(
                normalised,
                follower_count_start=follower_count_start,
                follower_count_end=follower_count_end,
            ),
            "engagement_rate_per_reach_pct": aggregate_engagement_rate(normalised),
            "interactions_per_1k_followers": interactions_per_1k_followers(
                total_engagements, total_followers,
            ),
            "total_saves": total_saves(normalised),
            "grade_distribution": grade_distribution(normalised),
            "graded_posts": [
                {
                    "id": p.get("id"),
                    "platform": p.get("platform"),
                    "score": p.get("score"),
                    "grade": p.get("grade"),
                }
                for p in normalised
            ],
        },
    }


@router.get("/audience/gender")
async def audience_gender(
    brand=Depends(require_brand),
) -> dict[str, Any]:
    """Audience gender split — drives the gender pie/donut on the Audience tab.

    Sources from Instagram for now (the only platform exposing real audience data on
    a Business account). Returns a normalised ``{ female, male, unspecified }`` dict
    so the FE chart doesn't have to interpret `F.25-34` style keys.
    """
    sess = _ig_session_for(brand.id)
    if not sess:
        raise HTTPException(status_code=404, detail="Instagram not connected for this brand")
    ig_user_id, token = sess

    raw = await InstagramInsightsService(access_token=token).fetch_audience_demographics(ig_user_id)
    gender_age = raw.get("audience_gender_age") or {}

    totals = {"female": 0, "male": 0, "unspecified": 0}
    for key, count in gender_age.items():
        # Keys are like "F.25-34", "M.18-24", "U.55+".
        prefix = (key or "").split(".", 1)[0].upper()
        if prefix == "F":
            totals["female"] += int(count or 0)
        elif prefix == "M":
            totals["male"] += int(count or 0)
        else:
            totals["unspecified"] += int(count or 0)

    return {"success": True, "data": totals}


@router.get("/audience/age")
async def audience_age(
    brand=Depends(require_brand),
) -> dict[str, Any]:
    """Audience age distribution — drives the age bar chart on the Audience tab.

    Returns ``{ "13-17": n, "18-24": n, "25-34": n, ... }`` summed across genders.
    """
    sess = _ig_session_for(brand.id)
    if not sess:
        raise HTTPException(status_code=404, detail="Instagram not connected for this brand")
    ig_user_id, token = sess

    raw = await InstagramInsightsService(access_token=token).fetch_audience_demographics(ig_user_id)
    gender_age = raw.get("audience_gender_age") or {}

    buckets: dict[str, int] = {}
    for key, count in gender_age.items():
        # "F.25-34" → "25-34"; preserve "55+" / "65+" style.
        parts = (key or "").split(".", 1)
        bucket = parts[1] if len(parts) == 2 else (parts[0] or "unknown")
        buckets[bucket] = buckets.get(bucket, 0) + int(count or 0)

    # Order by the standard IG bucket sequence so the FE chart x-axis is consistent.
    order = ("13-17", "18-24", "25-34", "35-44", "45-54", "55-64", "55+", "65+")
    ordered = {k: buckets.get(k, 0) for k in order if k in buckets}
    # Append any non-standard buckets at the end so we don't drop data.
    for k, v in buckets.items():
        if k not in ordered:
            ordered[k] = v

    return {"success": True, "data": ordered}


@router.get("/followers/growth")
async def followers_growth(
    brand=Depends(require_brand),
    since: str | None = Query(None),
    until: str | None = Query(None),
) -> dict[str, Any]:
    """Followers count at the start + end of the window + growth rate %.

    Drives the 'Followers growth Rate for the date filtered' tile in the top-of-page
    KPI row. Pulls from the Instagram time-series follower_count metric.
    """
    sess = _ig_session_for(brand.id)
    if not sess:
        raise HTTPException(status_code=404, detail="Instagram not connected for this brand")
    ig_user_id, token = sess

    win_since, win_until = parse_window(since, until)
    svc = InstagramInsightsService(access_token=token)
    raw = await svc.fetch_account_insights(
        ig_user_id,
        period="day",
        since=str(int(__import__("datetime").datetime.fromisoformat(win_since.isoformat()).timestamp())),
        until=str(int(__import__("datetime").datetime.fromisoformat(win_until.isoformat()).timestamp())),
        metrics=["follower_count"],
    )

    series = (svc._format_timeseries(raw) or {}).get("follower_count") or []
    start_value = int(series[0]["value"] or 0) if series else 0
    end_value = int(series[-1]["value"] or 0) if series else 0
    growth_rate = round(((end_value - start_value) / start_value) * 100.0, 2) if start_value else None

    return {
        "success": True,
        "data": {
            "period": {"since": win_since.isoformat(), "until": win_until.isoformat()},
            "follower_count_start": start_value,
            "follower_count_end": end_value,
            "growth_rate_pct": growth_rate,
            "series": series,
        },
    }
