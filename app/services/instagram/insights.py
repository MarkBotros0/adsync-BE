from typing import Any
from datetime import datetime, timedelta
from app.services.instagram.api_client import InstagramAPIClient

# Per-type metric lists (metrics differ by media_product_type)
_FEED_METRICS = [
    "impressions", "reach", "likes", "comments", "shares",
    "saved", "total_interactions", "profile_visits", "follows",
]
# video_views is only valid for feed VIDEO posts (not IMAGE or CAROUSEL_ALBUM)
_FEED_VIDEO_METRICS = _FEED_METRICS + ["video_views"]
_REEL_METRICS = [
    "plays", "reach", "likes", "comments", "shares",
    "saved", "total_interactions",
]
_STORY_METRICS = [
    "impressions", "reach", "exits", "taps_forward", "taps_back",
    "replies", "shares", "total_interactions", "profile_visits", "follows",
]

# Newer total_value-based account metrics — surfaced as headline KPIs.
_ENGAGEMENT_TOTAL_METRICS = [
    "total_interactions", "likes", "comments", "shares", "saves",
    "reach", "accounts_engaged", "replies",
    "profile_links_taps", "phone_call_clicks",
    "text_message_clicks", "get_directions_clicks",
]


class InstagramInsightsService(InstagramAPIClient):
    """Service for Instagram account-level and media-level insights."""

    # ── Account-level insights ────────────────────────────────────────────────

    async def fetch_account_insights(
        self,
        ig_user_id: str,
        period: str = "day",
        since: str | None = None,
        until: str | None = None,
        metrics: list[str] | None = None,
    ) -> dict[str, Any]:
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

        params: dict[str, Any] = {
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
    ) -> dict[str, Any]:
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
    ) -> dict[str, Any]:
        """Fetch aggregated engagement totals using the newer metric_type API.

        Includes the action-tap metrics (profile links, phone, text, directions) that
        were missing from the v1 set so the dashboard can show "what did people do
        when they reached the profile?".
        """
        try:
            return await self.get(
                f"{ig_user_id}/insights",
                params={
                    "metric": ",".join(_ENGAGEMENT_TOTAL_METRICS),
                    "metric_type": "total_value",
                    "timeframe": timeframe,
                },
            )
        except Exception as e:
            return {"data": [], "error": str(e)}

    async def fetch_engagement_totals(
        self, ig_user_id: str, days: int = 30
    ) -> dict[str, Any]:
        """Public wrapper exposing the engagement totals as a structured dict."""
        raw = await self._fetch_engagement_totals(
            ig_user_id, timeframe=_days_to_timeframe(days)
        )
        return self._format_engagement_totals(raw)

    async def fetch_reach_by_follow_type(
        self,
        ig_user_id: str,
        days: int = 30,
    ) -> dict[str, Any]:
        """Reach split by ``follow_type`` (FOLLOWER vs NON_FOLLOWER).

        Uses the v22 breakdowns API. Returns ``{ FOLLOWER: int, NON_FOLLOWER: int }``.
        """
        try:
            raw = await self.get(
                f"{ig_user_id}/insights",
                params={
                    "metric": "reach",
                    "metric_type": "total_value",
                    "breakdown": "follow_type",
                    "timeframe": _days_to_timeframe(days),
                },
            )
        except Exception as e:
            return {"breakdown": {}, "error": str(e)}

        bucket: dict[str, int] = {}
        for entry in raw.get("data", []):
            tv = entry.get("total_value") or {}
            for breakdown in tv.get("breakdowns", []):
                for v in breakdown.get("results", []):
                    key = "_".join(v.get("dimension_values") or []) or "unknown"
                    bucket[key] = bucket.get(key, 0) + int(v.get("value") or 0)
        return {"breakdown": bucket}

    async def fetch_reach_by_media_product_type(
        self,
        ig_user_id: str,
        days: int = 30,
    ) -> dict[str, Any]:
        """Reach split by ``media_product_type`` (POST vs REEL vs STORY)."""
        try:
            raw = await self.get(
                f"{ig_user_id}/insights",
                params={
                    "metric": "reach",
                    "metric_type": "total_value",
                    "breakdown": "media_product_type",
                    "timeframe": _days_to_timeframe(days),
                },
            )
        except Exception as e:
            return {"breakdown": {}, "error": str(e)}

        bucket: dict[str, int] = {}
        for entry in raw.get("data", []):
            tv = entry.get("total_value") or {}
            for breakdown in tv.get("breakdowns", []):
                for v in breakdown.get("results", []):
                    key = "_".join(v.get("dimension_values") or []) or "unknown"
                    bucket[key] = bucket.get(key, 0) + int(v.get("value") or 0)
        return {"breakdown": bucket}

    async def fetch_stories(self, ig_user_id: str, limit: int = 25) -> list[dict[str, Any]]:
        """List the brand's recent stories. The Stories edge only returns active items
        (24h window) — historic insights need to be polled before they expire.
        """
        try:
            raw = await self.get(
                f"{ig_user_id}/stories",
                params={
                    "fields": "id,media_type,media_url,permalink,thumbnail_url,timestamp",
                    "limit": limit,
                },
            )
            return raw.get("data", [])
        except Exception:
            return []

    async def fetch_story_insights(self, story_id: str) -> dict[str, Any]:
        """Per-story metrics: taps_forward / taps_back / exits / replies / reach.

        Stories disappear after 24h so this must be polled inside the window. The
        returned shape matches ``fetch_media_insights`` for a STORY product type.
        """
        return await self.fetch_media_insights(story_id, media_product_type="STORY")

    async def fetch_audience_demographics(self, ig_user_id: str) -> dict[str, Any]:
        """
        Fetch lifetime audience demographics:
        gender/age breakdown, top cities, top countries.
        """
        results: dict[str, Any] = {}

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
        media_type: str | None = None,
    ) -> dict[str, Any]:
        """
        Fetch insights for a single IG Media object.

        Args:
            media_id: IG Media ID.
            media_product_type: 'FEED', 'REELS', or 'STORY'.
                                Determines which metrics are requested.
            media_type: 'IMAGE', 'VIDEO', or 'CAROUSEL_ALBUM'.
                        When FEED + VIDEO, video_views is added to the metric list.
        """
        mpt = (media_product_type or "FEED").upper()
        mt = (media_type or "").upper()

        if mpt == "REELS":
            metrics = _REEL_METRICS
        elif mpt == "STORY":
            metrics = _STORY_METRICS
        elif mt == "VIDEO":
            # Feed video — include video_views (not available for IMAGE/CAROUSEL)
            metrics = _FEED_VIDEO_METRICS
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
        self, raw: dict[str, Any], media_product_type: str
    ) -> dict[str, Any]:
        data = raw.get("data", [])
        metrics: dict[str, int] = {}
        for item in data:
            name = item.get("name")
            values = item.get("values", [])
            if values:
                metrics[name] = values[0].get("value", 0)
        return {"media_product_type": media_product_type, "metrics": metrics}

    def _format_engagement_totals(self, raw: dict[str, Any]) -> dict[str, Any]:
        data = raw.get("data", [])
        result: dict[str, Any] = {m: 0 for m in _ENGAGEMENT_TOTAL_METRICS}
        for item in data:
            name = item.get("name")
            total_value = item.get("total_value", {})
            if isinstance(total_value, dict):
                result[name] = total_value.get("value", 0)
        return result

    def _format_timeseries(self, raw: dict[str, Any]) -> dict[str, Any]:
        data = raw.get("data", [])
        result: dict[str, Any] = {}
        for item in data:
            name = item.get("name")
            values = item.get("values", [])
            result[name] = [
                {"value": v.get("value", 0), "end_time": v.get("end_time")}
                for v in values
            ]
        return result

    def _format_demographics(self, raw: dict[str, Any]) -> dict[str, Any]:
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
