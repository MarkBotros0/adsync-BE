from typing import Any
from app.services.facebook.api_client import APIClient
from app.utils.exceptions import FacebookAPIError


# Per-reaction-type field expansions. Each requests a zero-row list with a summary
# count, aliased so the response carries `like.summary.total_count`, etc., side-by-side
# with the existing rolled-up `reactions.summary.total_count`.
_REACTION_TYPES: tuple[str, ...] = ("LIKE", "LOVE", "HAHA", "WOW", "SAD", "ANGRY")
_REACTION_FIELDS: str = ",".join(
    f"reactions.type({t}).limit(0).summary(total_count).as({t.lower()})"
    for t in _REACTION_TYPES
)

_POST_FIELDS: str = (
    "id,message,story,created_time,permalink_url,type,status_type,"
    "attachments{media_type,media,url,subattachments,type,title,description},"
    "shares,likes.summary(true),comments.summary(true),"
    "reactions.summary(true),"
    f"{_REACTION_FIELDS}"
)


class PagesService(APIClient):
    """Service for Facebook Pages operations"""

    async def fetch_pages(self) -> dict[str, Any]:
        """Fetch all pages the user manages"""
        return await self.get(
            "me/accounts",
            params={"fields": "id,name,access_token,category,followers_count,fan_count"}
        )

    async def fetch_page_posts(self, page_id: str, limit: int = 25) -> dict[str, Any]:
        """Fetch posts from a page with engagement + per-reaction-type breakdown.

        The reaction-type fields are aliased (``like``, ``love``, ``haha``, ``wow``,
        ``sad``, ``angry``) so callers can pluck them directly without re-issuing the
        request per type.
        """
        try:
            return await self.get(
                f"{page_id}/posts",
                params={"fields": _POST_FIELDS, "limit": limit},
            )
        except FacebookAPIError as e:
            # Code 10 = "Application does not have permission for this action" —
            # /posts is sometimes locked behind a different permission than /feed.
            if "10" in str(e):
                return await self.get(
                    f"{page_id}/feed",
                    params={"fields": _POST_FIELDS, "limit": limit},
                )
            raise


def extract_reaction_breakdown(post: dict[str, Any]) -> dict[str, int]:
    """Pull the six aliased reaction counts off a post payload into a flat dict.

    Helper used by every router/transformer that surfaces the breakdown — keeps the
    field-name knowledge in one place so renaming the alias doesn't require a sweep.
    """
    out: dict[str, int] = {}
    for reaction_type in _REACTION_TYPES:
        key = reaction_type.lower()
        node = post.get(key) or {}
        summary = node.get("summary") or {}
        out[key] = int(summary.get("total_count") or 0)
    return out
