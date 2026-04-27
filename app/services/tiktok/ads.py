"""TikTok Ads (Marketing API v1.3) service.

Currently the codebase has zero TikTok Ads coverage — this module establishes the
service layer. Mirrors ``app/services/facebook/ads.py``: account discovery, campaign /
adgroup / ad list, and a reporting wrapper that produces a normalised KPI row matching
the Facebook ad row shape so the unified ``/ads/feed`` endpoint can stack them.

Auth: requires the brand's TikTok session to have been issued for a Business account
with ad-account scopes. The session ``access_token`` is the marketer-level token.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


# Marketing API lives on a different host from the Open API used elsewhere.
_BASE_URL = "https://business-api.tiktok.com/open_api/v1.3"


# Reporting metrics — the v1.3 marketing-api union of "marketer needs to report this".
# Keeping the list central means every report level (account/campaign/ad) returns the
# same column set so the FE table can be schema-stable.
_REPORT_METRICS: tuple[str, ...] = (
    # Spend & delivery
    "spend",
    "impressions",
    "reach",
    "frequency",
    "clicks",
    # Rates
    "ctr",
    "cpc",
    "cpm",
    # Conversions
    "conversion",
    "cost_per_conversion",
    "conversion_rate",
    "real_time_conversion",
    "real_time_cost_per_conversion",
    # Video — TikTok's bread and butter
    "video_play_actions",
    "video_watched_2s",
    "video_watched_6s",
    "average_video_play",
    "average_video_play_per_user",
    "video_views_p25",
    "video_views_p50",
    "video_views_p75",
    "video_views_p100",
    # Engagement
    "likes",
    "comments",
    "shares",
    "follows",
    "profile_visits",
)


class TikTokAdsService:
    """TikTok Marketing API ad-insights service.

    Carries the user-level TikTok access token. All advertiser-scoped calls require
    the ``advertiser_id`` to be passed explicitly — TikTok's API does not infer it
    from the token like Meta does.
    """

    def __init__(self, access_token: str) -> None:
        self.access_token = access_token

    @property
    def _headers(self) -> dict[str, str]:
        return {"Access-Token": self.access_token, "Content-Type": "application/json"}

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(f"{_BASE_URL}/{path}", headers=self._headers, params=params)
            r.raise_for_status()
            data = r.json()
        if data.get("code", 0) != 0:
            raise Exception(f"TikTok Ads API error [{data.get('code')}]: {data.get('message', '')}")
        return data.get("data", {}) or {}

    # ── Account discovery ──────────────────────────────────────────────────

    async def list_advertisers(self, app_id: str, secret: str) -> list[dict[str, Any]]:
        """List the advertiser accounts this token can access. Drives the account picker.

        Note: the v1.3 endpoint takes the partner-app credentials, not the access token,
        as query params. Caller passes them in from settings.
        """
        data = await self._get(
            "oauth2/advertiser/get/",
            params={"app_id": app_id, "secret": secret, "access_token": self.access_token},
        )
        return data.get("list", [])

    async def list_campaigns(
        self, advertiser_id: str, page: int = 1, page_size: int = 100
    ) -> list[dict[str, Any]]:
        """List campaigns under an advertiser account."""
        data = await self._get(
            "campaign/get/",
            params={
                "advertiser_id": advertiser_id,
                "page": page,
                "page_size": page_size,
            },
        )
        return data.get("list", [])

    async def list_adgroups(
        self, advertiser_id: str, campaign_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """List adgroups, optionally filtered to specific campaigns."""
        params: dict[str, Any] = {"advertiser_id": advertiser_id, "page_size": 100}
        if campaign_ids:
            # TikTok wants the value JSON-encoded for filter args.
            import json
            params["filtering"] = json.dumps({"campaign_ids": campaign_ids})
        data = await self._get("adgroup/get/", params=params)
        return data.get("list", [])

    async def list_ads(
        self, advertiser_id: str, adgroup_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """List ads, optionally filtered to specific adgroups (drives per-creative table)."""
        params: dict[str, Any] = {"advertiser_id": advertiser_id, "page_size": 100}
        if adgroup_ids:
            import json
            params["filtering"] = json.dumps({"adgroup_ids": adgroup_ids})
        data = await self._get("ad/get/", params=params)
        return data.get("list", [])

    # ── Reporting ──────────────────────────────────────────────────────────

    async def fetch_report(
        self,
        advertiser_id: str,
        *,
        start_date: str,
        end_date: str,
        level: str = "AUCTION_ADVERTISER",
        dimensions: list[str] | None = None,
        metrics: list[str] | None = None,
        data_level: str = "AUCTION_ADVERTISER",
    ) -> list[dict[str, Any]]:
        """Synchronous reporting endpoint.

        ``level`` / ``data_level`` valid values:
            - AUCTION_ADVERTISER — account totals
            - AUCTION_CAMPAIGN   — per campaign
            - AUCTION_ADGROUP    — per adgroup
            - AUCTION_AD         — per ad
        ``dimensions`` defaults to ``["advertiser_id"]`` for the account level — bump to
        ``["campaign_id"]``, ``["adgroup_id"]``, or ``["ad_id"]`` for the lower levels.
        """
        import json
        dim = dimensions or self._default_dimensions(level)
        metric_list = list(metrics or _REPORT_METRICS)
        params: dict[str, Any] = {
            "advertiser_id": advertiser_id,
            "report_type": "BASIC",
            "data_level": data_level,
            "dimensions": json.dumps(dim),
            "metrics": json.dumps(metric_list),
            "start_date": start_date,
            "end_date": end_date,
            "page": 1,
            "page_size": 1000,
        }
        try:
            data = await self._get("report/integrated/get/", params=params)
        except Exception as exc:
            logger.warning("TikTok report fetch failed: %s", exc)
            return []
        return data.get("list", [])

    @staticmethod
    def _default_dimensions(level: str) -> list[str]:
        return {
            "AUCTION_ADVERTISER": ["advertiser_id"],
            "AUCTION_CAMPAIGN": ["campaign_id"],
            "AUCTION_ADGROUP": ["adgroup_id"],
            "AUCTION_AD": ["ad_id"],
        }.get(level, ["advertiser_id"])


# ── Normaliser (matches the FB ads row shape so /ads/feed can stack them) ───

def normalise_tiktok_row(row: dict[str, Any]) -> dict[str, Any]:
    """Flatten one TikTok report row into the same KPI schema as the FB ads row.

    TikTok wraps the metrics under ``metrics`` and the dimension keys at top level.
    """
    metrics = row.get("metrics") or {}
    dims = row.get("dimensions") or {}

    def _f(key: str) -> float:
        try:
            return float(metrics.get(key) or 0)
        except (TypeError, ValueError):
            return 0.0

    def _i(key: str) -> int:
        try:
            return int(float(metrics.get(key) or 0))
        except (TypeError, ValueError):
            return 0

    spend = _f("spend")
    impressions = _i("impressions")
    clicks = _i("clicks")
    conversions = _i("conversion")

    return {
        "platform": "tiktok",
        "account_id": dims.get("advertiser_id"),
        "campaign_id": dims.get("campaign_id"),
        "adset_id": dims.get("adgroup_id"),
        "ad_id": dims.get("ad_id"),

        "spend": round(spend, 2),
        "impressions": impressions,
        "reach": _i("reach"),
        "frequency": _f("frequency"),
        "clicks": clicks,

        "ctr": _f("ctr"),
        "cpc": _f("cpc"),
        "cpm": _f("cpm"),

        "purchases": conversions,
        "purchase_value": 0.0,  # TikTok doesn't expose purchase value natively
        "leads": 0,
        "roas": None,
        "cost_per_purchase": _f("cost_per_conversion") if conversions else None,
        "cost_per_lead": None,

        # Video retention — TikTok counts at fixed percentiles (no p95 like FB).
        "video_views": _i("video_play_actions"),
        "video_p25": _i("video_views_p25"),
        "video_p50": _i("video_views_p50"),
        "video_p75": _i("video_views_p75"),
        "video_p95": 0,
        "video_p100": _i("video_views_p100"),
        "video_thruplay": _i("video_watched_6s"),
        "video_avg_time_sec": _f("average_video_play"),
    }
