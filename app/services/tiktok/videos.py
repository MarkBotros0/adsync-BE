"""
TikTok video and user info services.
"""
from typing import Any

from app.services.tiktok.api_client import TikTokAPIClient

_VIDEO_FIELDS = (
    "id,title,video_description,create_time,cover_image_url,share_url,"
    "duration,height,width,like_count,comment_count,share_count,view_count,"
    "embed_html,embed_link"
)

_USER_FIELDS = (
    "open_id,union_id,avatar_url,avatar_url_100,avatar_large_url,display_name,"
    "bio_description,profile_deep_link,is_verified,username,"
    "follower_count,following_count,likes_count,video_count"
)


class TikTokVideoService(TikTokAPIClient):
    """Fetch and normalize TikTok video data."""

    async def fetch_user_info(self) -> dict[str, Any]:
        """GET /v2/user/info/ — returns the authenticated user's profile."""
        data = await self.get("user/info/", params={"fields": _USER_FIELDS})
        return data.get("data", {}).get("user", {})

    async def fetch_videos(
        self,
        max_count: int = 20,
        cursor: int | None = None,
    ) -> dict[str, Any]:
        """
        POST /v2/video/list/ — paginated list of the user's public videos.

        Args:
            max_count: Results per page (max 20).
            cursor: Pagination cursor (UTC Unix timestamp in ms). Fetches videos
                    created before this timestamp. Omit to start from the newest.
        """
        max_count = min(max_count, 20)
        body: dict[str, Any] = {"max_count": max_count}
        if cursor is not None:
            body["cursor"] = cursor

        data = await self.post("video/list/", params={"fields": _VIDEO_FIELDS}, body=body)
        return data.get("data", {})

    async def fetch_videos_by_ids(self, video_ids: list[str]) -> dict[str, Any]:
        """
        POST /v2/video/query/ — fetch specific videos by ID (max 20 per request).
        """
        video_ids = video_ids[:20]
        data = await self.post(
            "video/query/",
            params={"fields": _VIDEO_FIELDS},
            body={"filters": {"video_ids": video_ids}},
        )
        return data.get("data", {})

    def format_video_list(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Normalize the video list response into a consistent structure."""
        videos = raw_data.get("videos", [])
        has_more = raw_data.get("has_more", False)
        cursor = raw_data.get("cursor")

        formatted = []
        for v in videos:
            formatted.append({
                "id": v.get("id"),
                "title": v.get("title", ""),
                "description": v.get("video_description", ""),
                "created_at": v.get("create_time"),
                "cover_image_url": v.get("cover_image_url", ""),
                "share_url": v.get("share_url", ""),
                "duration": v.get("duration"),
                "dimensions": {
                    "height": v.get("height"),
                    "width": v.get("width"),
                },
                "engagement": {
                    "likes": v.get("like_count", 0),
                    "comments": v.get("comment_count", 0),
                    "shares": v.get("share_count", 0),
                    "views": v.get("view_count", 0),
                    "total": (
                        v.get("like_count", 0)
                        + v.get("comment_count", 0)
                        + v.get("share_count", 0)
                    ),
                },
                "embed_html": v.get("embed_html", ""),
                "embed_link": v.get("embed_link", ""),
            })

        return {
            "total": len(formatted),
            "videos": formatted,
            "paging": {
                "cursor": cursor,
                "has_more": has_more,
            },
        }
