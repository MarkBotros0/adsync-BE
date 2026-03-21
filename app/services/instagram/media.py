from typing import Dict, Any, Optional
from app.services.instagram.api_client import InstagramAPIClient

# Fields fetched for every feed media object
_MEDIA_FIELDS = (
    "id,caption,media_type,media_product_type,media_url,thumbnail_url,"
    "permalink,shortcode,timestamp,username,like_count,comments_count,"
    "is_comment_enabled,is_shared_to_feed"
)

# Fields for story objects (subset — stories have fewer accessible fields)
_STORY_FIELDS = (
    "id,media_type,media_product_type,media_url,thumbnail_url,"
    "permalink,timestamp,username"
)


class InstagramMediaService(InstagramAPIClient):
    """Service for fetching Instagram media (feed posts, reels, stories)."""

    async def fetch_media(
        self,
        ig_user_id: str,
        limit: int = 25,
        since: Optional[str] = None,
        until: Optional[str] = None,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fetch feed media (images, videos, reels, carousels) for an IG User.

        Args:
            ig_user_id: Instagram User ID.
            limit: Number of items per page (max 100).
            since: Unix timestamp — only return media after this time.
            until: Unix timestamp — only return media before this time.
            after: Cursor for the next page.
        """
        params: Dict[str, Any] = {
            "fields": _MEDIA_FIELDS,
            "limit": min(limit, 100),
        }
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        if after:
            params["after"] = after

        return await self.get(f"{ig_user_id}/media", params=params)

    async def fetch_stories(self, ig_user_id: str) -> Dict[str, Any]:
        """
        Fetch currently active stories for an IG User (24-hour window only).
        """
        return await self.get(
            f"{ig_user_id}/stories",
            params={"fields": _STORY_FIELDS},
        )

    async def fetch_single_media(self, media_id: str) -> Dict[str, Any]:
        """Fetch a single IG Media object with full metadata."""
        return await self.get(
            media_id,
            params={"fields": _MEDIA_FIELDS},
        )

    async def fetch_media_comments(
        self, media_id: str, limit: int = 50
    ) -> Dict[str, Any]:
        """
        Fetch top-level comments on an IG Media object.
        Returns up to 50 comments (API maximum) in reverse-chronological order.
        """
        return await self.get(
            f"{media_id}/comments",
            params={
                "fields": "id,text,timestamp,username,like_count,replies{id,text,timestamp,username}",
                "limit": min(limit, 50),
            },
        )

    async def fetch_carousel_children(self, media_id: str) -> Dict[str, Any]:
        """
        Fetch child media objects for a CAROUSEL_ALBUM.
        Returns an empty data list for non-carousel media.
        """
        return await self.get(
            f"{media_id}/children",
            params={"fields": "id,media_type,media_url,thumbnail_url"},
        )

    def format_media_list(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalise raw /media response into a clean structure."""
        items = raw_data.get("data", [])
        formatted = []
        for item in items:
            formatted.append({
                "id": item.get("id"),
                "caption": item.get("caption", ""),
                "media_type": item.get("media_type"),
                "media_product_type": item.get("media_product_type"),
                "media_url": item.get("media_url", ""),
                "thumbnail_url": item.get("thumbnail_url", ""),
                "permalink": item.get("permalink", ""),
                "shortcode": item.get("shortcode", ""),
                "timestamp": item.get("timestamp"),
                "username": item.get("username", ""),
                "engagement": {
                    "likes": item.get("like_count", 0),
                    "comments": item.get("comments_count", 0),
                },
                "is_comment_enabled": item.get("is_comment_enabled"),
                "is_shared_to_feed": item.get("is_shared_to_feed"),
            })
        return {
            "total": len(formatted),
            "media": formatted,
            "paging": raw_data.get("paging", {}),
        }
