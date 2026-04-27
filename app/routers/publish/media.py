"""Inline media endpoints used by the composer + publisher.

Media is NOT exposed as a managed library — there are no list, browse, or delete
routes. The composer uploads files inline as part of post creation; the publisher
loop reads them via /raw when it's time to push to the platform; the
``brand_identities``-style retention story is "they live as long as the post".
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from app.database import get_session_local
from app.dependencies import require_brand
from app.routers.publish.schemas import MediaAssetSummary
from app.services import storage

router = APIRouter(prefix="/publish/media", tags=["Publish - Media"])
logger = logging.getLogger(__name__)


@router.post("", response_model=MediaAssetSummary, status_code=status.HTTP_201_CREATED)
async def upload_media(
    upload: UploadFile = File(...),
    brand=Depends(require_brand),
) -> Any:
    """Upload an image or video; bytes stored inline in Postgres.

    Returns the asset row (without bytes). The composer holds the returned ``id``
    and attaches it to the draft; the publisher loop reads bytes back via ``/raw``.
    """
    db = get_session_local()()
    try:
        try:
            asset = await storage.store(
                db,
                brand_id=brand.id,
                upload=upload,
                uploader_user_id=getattr(brand, "owner_user_id", None),
            )
        except storage.StorageError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        return asset
    finally:
        db.close()


@router.get("/{asset_id}/raw")
async def stream_media(asset_id: int, brand=Depends(require_brand)) -> Any:
    """Stream the asset's bytes back. Used by the composer preview + by Instagram /
    TikTok publish steps that need a public URL for the media."""
    db = get_session_local()()
    try:
        asset = storage.read(db, asset_id=asset_id, brand_id=brand.id)
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        content = asset.content
        mime = asset.mime
        filename = asset.filename
    finally:
        db.close()

    def _gen():
        yield content

    return StreamingResponse(
        _gen(),
        media_type=mime,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
