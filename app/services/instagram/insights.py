from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from app.services.instagram.api_client import InstagramAPIClient

# Per-type metric lists (metrics differ by media_product_type)
_FEED_METRICS = [
    "impressions", "reach", "likes", "comments", "shares",
    "saved", "total_interactions", "profile_visits", "follows",
]
_REEL_METRICS = [
    "plays", "reach", "likes", "comments", "shares",
    "saved", "total_interactions",
]
_STORY_METRICS = [
    "impressions", "reach", "exits", "taps_forward", "taps_back",
    "replies", "total_interactions", "profile_visits", "follows",
]


class InstagramInsightsService(InstagramAPIClient):
    """Service for Instagram account-level and media-level insights."""

    # ── Account-level insights ────────────────────────────────────────────────

    async def fetch_account_insights(
        self,
        ig_user_id: str,
        period: str = "day",
        since: Optional[str] = None,
        until: Optional[str] = None,
        metrics: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Fetch time-series account-level metrics.

        Default metrics: reach, impressions, profile_views, follower_count,
        website_clicks, email_contacts.

        Args:
            ig_user_id: Instagram User ID.
            period: Aggregation period — 'day', 'week', 'days_28', 'month'.
            since: Unix timestamp for start of range.
            until: Unix timestamp for end of range.
            metrics: Override the default metric list.
        """
        if metrics is None:
            metrics = [
                "reach",
                "impressions",
                "profile_views",
                "follower_count",
                "website_clicks",
                "email_contacts",
            ]

        params: Dict[str, Any] = {
            "metric": ",".join(metrics),
            "period": period,
        }
        if since:
            params["since"] = since
        if until:
            params["until"] = until

        try:
            return await self.get(f"{ig_user_id}/insights", params=params)
        except Exception as e:
            return {"data": [], "error": str(e)}

    async def fetch_account_summary(
        self,
        ig_user_id: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Fetch a structured analytics summary for the last N days.

        Combines:
        - Time-series reach/impressions/profile_views/follower_count
        - Engagement metrics (total_interactions, likes, comments, shares, saves)
        - Audience demographics (lifetime)
        """
        until_dt = datetime.utcnow()
        since_dt = until_dt - timedelta(days=days)
        since_ts = str(int(since_dt.timestamp()))
        until_ts = str(int(until_dt.timestamp()))

        # --- engagement metrics (newer API — metric_type=total_value) ---
        engagement_raw = await self._fetch_engagement_totals(
            ig_user_id, timeframe=_days_to_timeframe(days)
        )

        # --- time-series reach / impressions / profile views ---
        timeseries_raw = await self.fetch_account_insights(
            ig_user_id,
            period="day",
            since=since_ts,
            until=until_ts,
            metrics=["reach", "impressions", "profile_views", "follower_count"],
        )

        # --- audience demographics (lifetime) ---
        demographics_raw = await self.fetch_audience_demographics(ig_user_id)

        return {
            "ig_user_id": ig_user_id,
            "date_range": {
                "since": since_dt.isoformat(),
                "until": until_dt.isoformat(),
                "days": days,
            },
            "engagement": self._format_engagement_totals(engagement_raw),
            "time_series": self._format_timeseries(timeseries_raw),
            "demographics": self._format_demographics(demographics_raw),
        }

    async def _fetch_engagement_totals(
        self, ig_user_id: str, timeframe: str = "last_30_days"
    ) -> Dict[str, Any]:
        """Fetch aggregated engagement totals using the newer metric_type API."""
        try:
            return await self.get(
                f"{ig_user_id}/insights",
                params={
                    "metric": "total_interactions,likes,comments,shares,saves,reach,accounts_engaged",
                    "metric_type": "total_value",
                    "timeframe": timeframe,
                },
            )
        except Exception as e:
            return {"data": [], "error": str(e)}

    async def fetch_audience_demographics(self, ig_user_id: str) -> Dict[str, Any]:
        """
        Fetch lifetime audience demographics:
        gender/age breakdown, top cities, top countries.
        """
        results: Dict[str, Any] = {}

        for metric, period in [
            ("audience_gender_age", "lifetime"),
            ("audience_city", "lifetime"),
            ("audience_country", "lifetime"),
            ("online_followers", "lifetime"),
        ]:
            try:
                resp = await self.get(
                    f"{ig_user_id}/insights",
                    params={"metric": metric, "period": period},
                )
                data = resp.get("data", [])
                results[metric] = data[0].get("values", [{}])[0].get("value", {}) if data else {}
            except Exception:
                results[metric] = {}

        return results

    # ── Media-level insights ─────────────────────────────────────────────────

    async def fetch_media_insights(
        self,
        media_id: str,
        media_product_type: str = "FEED",
    ) -> Dict[str, Any]:
        """
        Fetch insights for a single IG Media object.

        Args:
            media_id: IG Media ID.
            media_product_type: 'FEED', 'REELS', or 'STORY'.
                                Determines which metrics are requested.
        """
        mpt = (media_product_type or "FEED").upper()

        if mpt == "REELS":
            metrics = _REEL_METRICS
        elif mpt == "STORY":
            metrics = _STORY_METRICS
        else:
            metrics = _FEED_METRICS

        try:
            raw = await self.get(
                f"{media_id}/insights",
                params={"metric": ",".join(metrics)},
            )
            return self._format_media_insights(raw, mpt)
        except Exception as e:
            return {"media_id": media_id, "error": str(e), "metrics": {}}

    # ── Formatters ───────────────────────────────────────────────────────────

    def _format_media_insights(
        self, raw: Dict[str, Any], media_product_type: str
    ) -> Dict[str, Any]:
        data = raw.get("data", [])
        metrics: Dict[str, int] = {}
        for item in data:
            name = item.get("name")
            values = item.get("values", [])
            if values:
                metrics[name] = values[0].get("value", 0)
        return {"media_product_type": media_product_type, "metrics": metrics}

    def _format_engagement_totals(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        data = raw.get("data", [])
        result: Dict[str, Any] = {
            "total_interactions": 0,
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "saves": 0,
            "reach": 0,
            "accounts_engaged": 0,
        }
        for item in data:
            name = item.get("name")
            total_value = item.get("total_value", {})
            if isinstance(total_value, dict):
                result[name] = total_value.get("value", 0)
        return result

    def _format_timeseries(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        data = raw.get("data", [])
        result: Dict[str, Any] = {}
        for item in data:
            name = item.get("name")
            values = item.get("values", [])
            result[name] = [
                {"value": v.get("value", 0), "end_time": v.get("end_time")}
                for v in values
            ]
        return result

    def _format_demographics(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "gender_age": raw.get("audience_gender_age", {}),
            "top_cities": raw.get("audience_city", {}),
            "top_countries": raw.get("audience_country", {}),
            "online_followers_by_hour": raw.get("online_followers", {}),
        }


def _days_to_timeframe(days: int) -> str:
    """Map a day count to the nearest supported Instagram timeframe value."""
    if days <= 14:
        return "last_14_days"
    if days <= 30:
        return "last_30_days"
    if days <= 90:
        return "last_90_days"
    return "last_90_days"
