"""Facebook Marketing API — Ad Insights service.

Goes well beyond the legacy ``clicks/impressions/spend`` triple. Pulls the full marketer
KPI set (CPM, CPC, CTR, ROAS, conversions, video retention p25→p100) and provides
helpers for account / campaign / ad-level queries.
"""
from __future__ import annotations

from typing import Any

from app.services.facebook.api_client import APIClient
from app.utils.exceptions import FacebookAPIError


# Field set requested for every insights query. Centralised so account / campaign / ad
# level all return the same shape and the response normaliser is one function.
_INSIGHTS_FIELDS: tuple[str, ...] = (
    # Spend & delivery
    "spend",
    "impressions",
    "reach",
    "frequency",
    "clicks",
    # Rate-based KPIs
    "ctr",
    "cpc",
    "cpm",
    "cpp",
    # Unique versions
    "unique_clicks",
    "unique_ctr",
    "unique_actions",
    "cost_per_unique_action_type",
    # Outbound (clicks that left FB) — usually the more honest CTR for marketers
    "outbound_clicks",
    "outbound_clicks_ctr",
    "cost_per_outbound_click",
    # Conversions & ROAS
    "actions",
    "action_values",
    "conversions",
    "cost_per_action_type",
    "cost_per_conversion",
    "purchase_roas",
    "website_purchase_roas",
    # Video retention
    "video_p25_watched_actions",
    "video_p50_watched_actions",
    "video_p75_watched_actions",
    "video_p95_watched_actions",
    "video_p100_watched_actions",
    "video_avg_time_watched_actions",
    "video_thruplay_watched_actions",
    "video_play_actions",
    # Identity (so the FE can join across calls)
    "account_id",
    "campaign_id",
    "campaign_name",
    "adset_id",
    "adset_name",
    "ad_id",
    "ad_name",
    "date_start",
    "date_stop",
)


def _params(
    *,
    since: str | None,
    until: str | None,
    level: str | None = None,
    breakdowns: list[str] | None = None,
    time_increment: int | str | None = None,
    extra_fields: list[str] | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Build a params dict for the /insights edge — used by every call below."""
    fields = list(_INSIGHTS_FIELDS) + (extra_fields or [])
    params: dict[str, Any] = {"fields": ",".join(fields)}
    if level:
        params["level"] = level
    if since and until:
        params["time_range"] = f'{{"since":"{since}","until":"{until}"}}'
    if breakdowns:
        params["breakdowns"] = ",".join(breakdowns)
    if time_increment is not None:
        params["time_increment"] = str(time_increment)
    if limit is not None:
        params["limit"] = str(limit)
    return params


class AdsService(APIClient):
    """Facebook Marketing API ad-insights service."""

    # ── Account discovery ───────────────────────────────────────────────────

    async def fetch_ad_accounts(self) -> dict[str, Any]:
        """List the user's ad accounts. Drives the picker on the ads dashboard."""
        return await self.get(
            "me/adaccounts",
            params={"fields": "account_id,id,name,currency,account_status,timezone_name,business_name"},
        )

    async def fetch_campaigns(self, account_id: str, limit: int = 100) -> dict[str, Any]:
        """List campaigns under an ad account."""
        return await self.get(
            f"{account_id}/campaigns",
            params={
                "fields": "id,name,objective,status,effective_status,start_time,stop_time,daily_budget,lifetime_budget",
                "limit": limit,
            },
        )

    async def fetch_ads(self, adset_or_campaign_id: str, limit: int = 100) -> dict[str, Any]:
        """List ads under a campaign or adset (creative thumbnails for the per-ad table)."""
        return await self.get(
            f"{adset_or_campaign_id}/ads",
            params={
                "fields": "id,name,status,effective_status,creative{id,name,thumbnail_url,image_url,object_story_spec},updated_time",
                "limit": limit,
            },
        )

    # ── Insights queries ────────────────────────────────────────────────────

    async def fetch_account_insights(
        self,
        account_id: str,
        since: str | None = None,
        until: str | None = None,
        time_increment: int | str | None = None,
    ) -> dict[str, Any]:
        """Account-level KPI summary (one row per period if time_increment set)."""
        try:
            return await self.get(
                f"{account_id}/insights",
                params=_params(since=since, until=until, level="account", time_increment=time_increment),
            )
        except FacebookAPIError as exc:
            return {"data": [], "error": str(exc)}

    async def fetch_campaign_insights(
        self,
        account_id: str,
        since: str | None = None,
        until: str | None = None,
    ) -> dict[str, Any]:
        """Campaign-level breakdown — one row per campaign in the window."""
        try:
            return await self.get(
                f"{account_id}/insights",
                params=_params(since=since, until=until, level="campaign", limit=200),
            )
        except FacebookAPIError as exc:
            return {"data": [], "error": str(exc)}

    async def fetch_ad_insights(
        self,
        account_id: str,
        since: str | None = None,
        until: str | None = None,
    ) -> dict[str, Any]:
        """Ad-level breakdown — one row per ad in the window. Drives the per-creative table."""
        try:
            return await self.get(
                f"{account_id}/insights",
                params=_params(since=since, until=until, level="ad", limit=500),
            )
        except FacebookAPIError as exc:
            return {"data": [], "error": str(exc)}

    async def fetch_account_demographics(
        self,
        account_id: str,
        since: str | None = None,
        until: str | None = None,
    ) -> dict[str, Any]:
        """Spend / impressions / clicks / conversions broken down by age × gender."""
        try:
            return await self.get(
                f"{account_id}/insights",
                params=_params(
                    since=since,
                    until=until,
                    level="account",
                    breakdowns=["age", "gender"],
                ),
            )
        except FacebookAPIError as exc:
            return {"data": [], "error": str(exc)}

    async def fetch_account_geo(
        self,
        account_id: str,
        since: str | None = None,
        until: str | None = None,
    ) -> dict[str, Any]:
        """Spend / impressions / conversions by country."""
        try:
            return await self.get(
                f"{account_id}/insights",
                params=_params(
                    since=since,
                    until=until,
                    level="account",
                    breakdowns=["country"],
                ),
            )
        except FacebookAPIError as exc:
            return {"data": [], "error": str(exc)}

    async def fetch_account_placement(
        self,
        account_id: str,
        since: str | None = None,
        until: str | None = None,
    ) -> dict[str, Any]:
        """Spend / KPIs by placement (FB feed vs IG feed vs Stories vs Reels etc)."""
        try:
            return await self.get(
                f"{account_id}/insights",
                params=_params(
                    since=since,
                    until=until,
                    level="account",
                    breakdowns=["publisher_platform", "platform_position"],
                ),
            )
        except FacebookAPIError as exc:
            return {"data": [], "error": str(exc)}


# ── Response normaliser ─────────────────────────────────────────────────────


def _action_value(actions: list[dict[str, Any]] | None, action_type: str) -> float:
    """Sum the ``value`` of each action whose ``action_type`` matches.

    Facebook returns ``actions`` and ``action_values`` as lists of ``{action_type, value}``
    rows; we collapse to a flat number per type so the FE doesn't deal with the structure.
    """
    if not actions:
        return 0.0
    total = 0.0
    for a in actions:
        if a.get("action_type") == action_type:
            try:
                total += float(a.get("value") or 0)
            except (TypeError, ValueError):
                pass
    return total


def _video_views(retention_actions: list[dict[str, Any]] | None) -> int:
    """Pull the ``video_view`` count out of a retention-action list."""
    if not retention_actions:
        return 0
    for a in retention_actions:
        if a.get("action_type") == "video_view":
            try:
                return int(float(a.get("value") or 0))
            except (TypeError, ValueError):
                return 0
    return 0


def normalise_insights_row(row: dict[str, Any]) -> dict[str, Any]:
    """Flatten one Marketing-API insights row into a chart-friendly shape.

    Keeps every numeric KPI a marketer would want at top-level so the FE does not have
    to re-parse the action arrays.
    """
    spend = float(row.get("spend") or 0)
    impressions = int(row.get("impressions") or 0)
    reach = int(row.get("reach") or 0)
    clicks = int(row.get("clicks") or 0)
    actions = row.get("actions") or []
    action_values = row.get("action_values") or []

    purchases = _action_value(actions, "purchase") or _action_value(actions, "omni_purchase")
    purchase_value = _action_value(action_values, "purchase") or _action_value(action_values, "omni_purchase")
    leads = _action_value(actions, "lead") or _action_value(actions, "onsite_conversion.lead_grouped")
    add_to_cart = _action_value(actions, "add_to_cart") or _action_value(actions, "omni_add_to_cart")
    initiated_checkout = _action_value(actions, "initiate_checkout") or _action_value(actions, "omni_initiated_checkout")

    purchase_roas_list = row.get("purchase_roas") or []
    roas = float(purchase_roas_list[0]["value"]) if purchase_roas_list and "value" in purchase_roas_list[0] else None

    outbound_clicks = _action_value(row.get("outbound_clicks"), "outbound_click")
    outbound_ctr_list = row.get("outbound_clicks_ctr") or []
    outbound_ctr = float(outbound_ctr_list[0]["value"]) if outbound_ctr_list and "value" in outbound_ctr_list[0] else None

    return {
        "account_id": row.get("account_id"),
        "campaign_id": row.get("campaign_id"),
        "campaign_name": row.get("campaign_name"),
        "adset_id": row.get("adset_id"),
        "adset_name": row.get("adset_name"),
        "ad_id": row.get("ad_id"),
        "ad_name": row.get("ad_name"),
        "date_start": row.get("date_start"),
        "date_stop": row.get("date_stop"),

        # Delivery
        "spend": round(spend, 2),
        "impressions": impressions,
        "reach": reach,
        "frequency": float(row.get("frequency") or 0),
        "clicks": clicks,
        "outbound_clicks": int(outbound_clicks),

        # Rates
        "ctr": float(row.get("ctr") or 0),
        "cpc": float(row.get("cpc") or 0),
        "cpm": float(row.get("cpm") or 0),
        "cpp": float(row.get("cpp") or 0),
        "outbound_ctr": outbound_ctr,
        "unique_ctr": float(row.get("unique_ctr") or 0),

        # Conversions
        "purchases": int(purchases),
        "purchase_value": round(purchase_value, 2),
        "leads": int(leads),
        "add_to_cart": int(add_to_cart),
        "initiated_checkout": int(initiated_checkout),
        "roas": roas,
        "cost_per_purchase": round(spend / purchases, 2) if purchases else None,
        "cost_per_lead": round(spend / leads, 2) if leads else None,

        # Video retention curve (raw counts)
        "video_views": _video_views(row.get("video_play_actions")),
        "video_p25": _video_views(row.get("video_p25_watched_actions")),
        "video_p50": _video_views(row.get("video_p50_watched_actions")),
        "video_p75": _video_views(row.get("video_p75_watched_actions")),
        "video_p95": _video_views(row.get("video_p95_watched_actions")),
        "video_p100": _video_views(row.get("video_p100_watched_actions")),
        "video_thruplay": _video_views(row.get("video_thruplay_watched_actions")),
        "video_avg_time_sec": _video_views(row.get("video_avg_time_watched_actions")),
    }


def aggregate_totals(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Roll a list of normalised rows into a single account-level totals object.

    Sums additive KPIs and recomputes derived rates (CTR/CPC/CPM/ROAS) on the totals,
    which is the correct way to aggregate — averaging rates would weight every row equally.
    """
    if not rows:
        return {}

    spend = sum(r["spend"] for r in rows)
    impressions = sum(r["impressions"] for r in rows)
    reach = sum(r["reach"] for r in rows)
    clicks = sum(r["clicks"] for r in rows)
    outbound_clicks = sum(r["outbound_clicks"] for r in rows)
    purchases = sum(r["purchases"] for r in rows)
    purchase_value = sum(r["purchase_value"] for r in rows)
    leads = sum(r["leads"] for r in rows)

    return {
        "spend": round(spend, 2),
        "impressions": impressions,
        "reach": reach,
        "clicks": clicks,
        "outbound_clicks": outbound_clicks,
        "purchases": purchases,
        "purchase_value": round(purchase_value, 2),
        "leads": leads,
        "ctr": round((clicks / impressions) * 100, 4) if impressions else 0.0,
        "cpc": round(spend / clicks, 4) if clicks else 0.0,
        "cpm": round((spend / impressions) * 1000, 4) if impressions else 0.0,
        "frequency": round(impressions / reach, 2) if reach else 0.0,
        "outbound_ctr": round((outbound_clicks / impressions) * 100, 4) if impressions else 0.0,
        "roas": round(purchase_value / spend, 2) if spend else None,
        "cost_per_purchase": round(spend / purchases, 2) if purchases else None,
        "cost_per_lead": round(spend / leads, 2) if leads else None,
    }
