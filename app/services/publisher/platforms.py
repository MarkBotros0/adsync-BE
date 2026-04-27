"""Per-platform publish helpers — turn a ScheduledPost row into a platform API call.

Each helper returns the platform's post ID on success. Failures raise; the loop
catches and updates the row with ``error_message`` + retry bookkeeping.

References:
- Facebook: ``Docs/facebook/03_pages_api.md``
- Instagram: ``Docs/instagram/05_content_publishing_api.md`` (two-step container then publish)
- TikTok: ``Docs/tiktok/05_content_posting_api.md`` (PULL-from-URL or chunked PUSH)
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.config import get_settings
from app.models.media_asset import MediaAssetModel

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Facebook ────────────────────────────────────────────────────────────────

async def publish_to_facebook(
    *,
    page_id: str,
    page_token: str,
    text: str,
    media: list[MediaAssetModel],
) -> str:
    """Publish to a Facebook Page. Text-only → /feed; single image → /photos; video → /videos.

    Multi-image posts use the unpublished-photos + /feed attached_media pattern.
    """
    base = f"https://graph.facebook.com/{settings.facebook_api_version}/{page_id}"

    # Text-only post.
    if not media:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(f"{base}/feed", data={"message": text, "access_token": page_token})
            r.raise_for_status()
            return r.json()["id"]

    # Single image.
    if len(media) == 1 and media[0].kind == "image":
        async with httpx.AsyncClient(timeout=60) as c:
            files = {"source": (media[0].filename, media[0].content, media[0].mime)}
            r = await c.post(
                f"{base}/photos",
                data={"caption": text, "access_token": page_token},
                files=files,
            )
            r.raise_for_status()
            data = r.json()
            return data.get("post_id") or data.get("id")

    # Single video.
    if len(media) == 1 and media[0].kind == "video":
        async with httpx.AsyncClient(timeout=120) as c:
            files = {"source": (media[0].filename, media[0].content, media[0].mime)}
            r = await c.post(
                f"{base}/videos",
                data={"description": text, "access_token": page_token},
                files=files,
            )
            r.raise_for_status()
            return r.json()["id"]

    # Multi-image carousel: upload each as unpublished, then attach.
    async with httpx.AsyncClient(timeout=120) as c:
        media_fbids: list[str] = []
        for asset in media:
            files = {"source": (asset.filename, asset.content, asset.mime)}
            r = await c.post(
                f"{base}/photos",
                data={"published": "false", "access_token": page_token},
                files=files,
            )
            r.raise_for_status()
            media_fbids.append(r.json()["id"])
        attached = [{"media_fbid": mid} for mid in media_fbids]
        r = await c.post(
            f"{base}/feed",
            data={
                "message": text,
                "attached_media": str(attached).replace("'", '"'),
                "access_token": page_token,
            },
        )
        r.raise_for_status()
        return r.json()["id"]


# ── Instagram ───────────────────────────────────────────────────────────────

async def publish_to_instagram(
    *,
    ig_user_id: str,
    access_token: str,
    text: str,
    media_url: str | None,  # IG requires PUBLICLY accessible URL — see note below
    is_video: bool = False,
) -> str:
    """Two-step publish: create container → publish container.

    NOTE — Instagram's API requires media to be hosted at a public URL it can fetch.
    Since we store bytes in Postgres, the FE/server must first expose the asset via
    ``/publish/media/{id}/raw`` over a public hostname (or a temporary signed URL via
    a tunnel like ngrok in dev). This function takes the resolved ``media_url`` to
    keep the publish step pure.
    """
    if not media_url:
        raise ValueError("Instagram requires a media_url; text-only posts are not supported")

    base = f"https://graph.instagram.com/v22.0/{ig_user_id}"
    async with httpx.AsyncClient(timeout=60) as c:
        # Step 1: create container.
        container_params = {"access_token": access_token, "caption": text}
        if is_video:
            container_params["media_type"] = "VIDEO"
            container_params["video_url"] = media_url
        else:
            container_params["image_url"] = media_url
        r = await c.post(f"{base}/media", params=container_params)
        r.raise_for_status()
        creation_id = r.json()["id"]

        # Step 2: poll until container is ready (only really needed for videos).
        if is_video:
            for _ in range(30):
                status_r = await c.get(
                    f"https://graph.instagram.com/v22.0/{creation_id}",
                    params={"access_token": access_token, "fields": "status_code"},
                )
                status_r.raise_for_status()
                code = status_r.json().get("status_code")
                if code == "FINISHED":
                    break
                if code == "ERROR":
                    raise RuntimeError("Instagram media upload failed")
                await asyncio.sleep(2)

        # Step 3: publish.
        r = await c.post(
            f"{base}/media_publish",
            params={"access_token": access_token, "creation_id": creation_id},
        )
        r.raise_for_status()
        return r.json()["id"]


# ── TikTok ──────────────────────────────────────────────────────────────────

async def publish_to_tiktok(
    *,
    access_token: str,
    text: str,
    media: list[MediaAssetModel],
) -> str:
    """Direct Post a video to TikTok using the Content Posting API (PULL_FROM_URL flavor).

    NOTE — like Instagram, TikTok requires a publicly fetchable URL for the video.
    For an in-process publisher with no S3, the FE serves the asset via
    ``/publish/media/{id}/raw`` over the brand's public host. This function takes the
    resolved URL via ``media[0].public_url`` set by the loop.
    """
    if not media:
        raise ValueError("TikTok requires a video media asset")
    asset = media[0]
    if asset.kind != "video":
        raise ValueError("TikTok only supports video posts")
    public_url = getattr(asset, "public_url", None)
    if not public_url:
        raise ValueError("Asset has no public_url resolved by the loop")

    async with httpx.AsyncClient(timeout=60) as c:
        # Init the post.
        r = await c.post(
            "https://open.tiktokapis.com/v2/post/publish/video/init/",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json={
                "post_info": {
                    "title": text[:150],
                    "privacy_level": "PUBLIC_TO_EVERYONE",
                    "disable_duet": False,
                    "disable_comment": False,
                    "disable_stitch": False,
                },
                "source_info": {
                    "source": "PULL_FROM_URL",
                    "video_url": public_url,
                },
            },
        )
        r.raise_for_status()
        publish_id = r.json()["data"]["publish_id"]
        return publish_id
