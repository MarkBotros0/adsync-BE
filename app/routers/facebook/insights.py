"""Facebook page-insights endpoints (demographics, reach split, frequency).

Brand-JWT authenticated — sessions are resolved server-side from the bearer token via
``require_brand``. The legacy session_id-style endpoints in ``pages.py`` are left alone
so existing FE code keeps working.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_session_local
from app.dependencies import require_brand
from app.repositories.facebook_session import FacebookSessionRepository
from app.services.facebook.insights import InsightsService
from app.services.facebook.pages import PagesService
from app.services.insights.period_compare import compare_periods, parse_window
from app.utils.exceptions import FacebookAPIError

router = APIRouter(prefix="/facebook/insights", tags=["Facebook Insights"])
logger = logging.getLogger(__name__)


async def _resolve_page(brand_id: int) -> tuple[str, str, str]:
    """Resolve the brand's first connected FB Page → (page_id, page_token, page_name).

    Mirrors the lookup pattern in ``app/routers/content/feed.py``.
    """
    db = get_session_local()()
    try:
        fb_session = FacebookSessionRepository(db).get_by_brand_id(brand_id)
        if not fb_session:
            raise HTTPException(status_code=404, detail="Facebook not connected for this brand")
        user_token = fb_session.access_token
    finally:
        db.close()

    pages_svc = PagesService(access_token=user_token)
    pages_data = await pages_svc.fetch_pages()
    pages = pages_data.get("data", [])
    if not pages:
        raise HTTPException(status_code=404, detail="No Facebook Pages on this account")

    page = pages[0]
    return page["id"], page.get("access_token", user_token), page.get("name", "")


def _to_unix(iso_date: str) -> str:
    """Convert ``YYYY-MM-DD`` to a Unix timestamp string for Graph API ``since``/``until``."""
    from datetime import datetime
    return str(int(datetime.fromisoformat(iso_date).timestamp()))


# ── Demographics ─────────────────────────────────────────────────────────────

@router.get("/page/demographics")
async def get_page_demographics(
    brand=Depends(require_brand),
    since: str | None = Query(None, description="ISO date — inclusive start of window"),
    until: str | None = Query(None, description="ISO date — inclusive end of window"),
) -> dict[str, Any]:
    """Audience age × gender, top cities, top countries, top languages.

    Each section is a `{ key: count }` map — sum across the window. The FE renders
    age/gender as a pyramid and city/country/locale as sortable lists or maps.
    """
    page_id, page_token, page_name = await _resolve_page(brand.id)
    win_since, win_until = parse_window(since, until)

    svc = InsightsService(access_token=page_token)
    try:
        result = await svc.fetch_page_demographics(
            page_id,
            since=_to_unix(win_since.isoformat()),
            until=_to_unix(win_until.isoformat()),
        )
    except FacebookAPIError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "success": True,
        "data": {
            "page_id": page_id,
            "page_name": page_name,
            "period": {"since": win_since.isoformat(), "until": win_until.isoformat()},
            "demographics": result["demographics"],
        },
    }


# ── Reach split (paid vs organic vs viral) ───────────────────────────────────

@router.get("/page/reach-breakdown")
async def get_page_reach_breakdown(
    brand=Depends(require_brand),
    since: str | None = Query(None),
    until: str | None = Query(None),
    compare: bool = Query(False, description="Also fetch the previous equal-length window"),
) -> dict[str, Any]:
    """Daily paid / organic / viral reach + impression series for the window.

    With ``compare=true`` a parallel call returns the immediately preceding window so
    the chart can render a faded baseline overlay.
    """
    page_id, page_token, page_name = await _resolve_page(brand.id)
    win_since, win_until = parse_window(since, until)

    svc = InsightsService(access_token=page_token)

    async def _fetch(s, u):
        return await svc.fetch_page_reach_breakdown(
            page_id, since=_to_unix(s.isoformat()), until=_to_unix(u.isoformat())
        )

    if compare:
        comparison = await compare_periods(
            _fetch, win_since, win_until,
            aggregator=lambda r: sum(
                sum((row.get("value") or 0) for row in series)
                for series in (r.get("series") or {}).values()
            ),
        )
        return {"success": True, "data": comparison}

    result = await _fetch(win_since, win_until)
    return {
        "success": True,
        "data": {
            "page_id": page_id,
            "page_name": page_name,
            "period": {"since": win_since.isoformat(), "until": win_until.isoformat()},
            "series": result["series"],
        },
    }


# ── Frequency distribution ───────────────────────────────────────────────────

@router.get("/page/frequency")
async def get_page_frequency(
    brand=Depends(require_brand),
    since: str | None = Query(None),
    until: str | None = Query(None),
) -> dict[str, Any]:
    """Frequency-distribution histogram: how many times the audience saw us.

    Returns ``[{ bucket: "1", count: N }, { bucket: "2", count: N }, ...]`` summed over
    the window. Buckets follow Meta's convention (``"1"``, ``"2"``, ``"3-5"``, ``"6+"``).
    """
    page_id, page_token, page_name = await _resolve_page(brand.id)
    win_since, win_until = parse_window(since, until)

    svc = InsightsService(access_token=page_token)
    try:
        result = await svc.fetch_page_frequency(
            page_id,
            since=_to_unix(win_since.isoformat()),
            until=_to_unix(win_until.isoformat()),
        )
    except FacebookAPIError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "success": True,
        "data": {
            "page_id": page_id,
            "page_name": page_name,
            "period": {"since": win_since.isoformat(), "until": win_until.isoformat()},
            "distribution": result["distribution"],
        },
    }
