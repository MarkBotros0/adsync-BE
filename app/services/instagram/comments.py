"""Instagram comments service — fetches a media's comment thread and analyses sentiment.

Sits on top of the existing ``InstagramMediaService.fetch_media_comments`` which already
requests text + replies. This module flattens the thread, runs each comment through the
in-process sentiment classifier, and produces a per-thread roll-up.
"""
from __future__ import annotations

from typing import Any

from app.services.analytics.sentiment import classify, summarise
from app.services.instagram.media import InstagramMediaService


class InstagramCommentsService:
    """Read + classify the comment thread of a single IG media object."""

    def __init__(self, access_token: str) -> None:
        self._media = InstagramMediaService(access_token=access_token)

    async def fetch_with_sentiment(
        self,
        media_id: str,
        limit: int = 50,
        include_replies: bool = True,
    ) -> dict[str, Any]:
        """Return the comment thread + per-comment sentiment + thread roll-up.

        Shape:
            {
              "media_id": str,
              "summary": { positive, neutral, negative, total, positive_pct, negative_pct },
              "comments": [
                { id, text, timestamp, username, like_count, sentiment,
                  replies?: [ { id, text, timestamp, username, sentiment } ] }
              ]
            }
        """
        try:
            raw = await self._media.fetch_media_comments(media_id, limit=limit)
        except Exception as exc:
            return {"media_id": media_id, "error": str(exc), "comments": [], "summary": {
                "total": 0, "positive": 0, "neutral": 0, "negative": 0,
                "positive_pct": 0.0, "negative_pct": 0.0,
            }}

        flat: list[dict[str, Any]] = []
        comments: list[dict[str, Any]] = []
        for c in raw.get("data", []):
            entry: dict[str, Any] = {
                "id": c.get("id"),
                "text": c.get("text") or "",
                "timestamp": c.get("timestamp"),
                "username": c.get("username"),
                "like_count": int(c.get("like_count") or 0),
                "sentiment": classify(c.get("text") or ""),
            }
            flat.append(entry)
            if include_replies:
                replies_raw = (c.get("replies") or {}).get("data") or []
                replies: list[dict[str, Any]] = []
                for r in replies_raw:
                    rep = {
                        "id": r.get("id"),
                        "text": r.get("text") or "",
                        "timestamp": r.get("timestamp"),
                        "username": r.get("username"),
                        "sentiment": classify(r.get("text") or ""),
                    }
                    replies.append(rep)
                    flat.append(rep)
                entry["replies"] = replies
            comments.append(entry)

        # ``summarise`` recomputes sentiment + counts off the flat list — cheaper than
        # re-classifying and keeps a single source of truth for the roll-up math.
        summary = summarise(flat)

        return {
            "media_id": media_id,
            "summary": summary,
            "comments": comments,
        }
