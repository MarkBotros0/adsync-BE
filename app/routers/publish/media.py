"""Media library endpoints — upload + list + stream + delete (Postgres-backed)."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse

from app.database import get_session_local
from app.dependencies import require_brand
from app.models.media_asset import KIND_IMAGE, KIND_VIDEO
from app.routers.publish.schemas import MediaAssetSummary
from app.services import storage

router = APIRouter(prefix="/publish/media", tags=["Publish - Media"])
logger = logging.getLogger(__name__)


@router.get("", response_model=list[MediaAssetSummary])
async def list_media(
    brand=Depends(require_brand),
    kind: str | None = Query(None, description="image | video"),
    limit: int = Query(100, ge=1, le=500),
) -> Any:
    """List media assets for the current brand, newest first. Bytes never returned here."""
    if kind and kind not in (KIND_IMAGE, KIND_VIDEO):
        raise HTTPException(status_code=422, detail="kind must be 'image' or 'video'")
    db = get_session_local()()
    try:
        return storage.list_for_brand(db, brand_id=brand.id, kind=kind, limit=limit)
    finally:
        db.close()


@router.post("", response_model=MediaAssetSummary, status_code=status.HTTP_201_CREATED)
async def upload_media(
    upload: UploadFile = File(...),
    brand=Depends(require_brand),
) -> Any:
    """Upload an image or video; bytes are stored inline in Postgres."""
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
    """Stream the asset's bytes back to the client. Brand-JWT scoped."""
    db = get_session_local()()
    try:
        asset = storage.read(db, asset_id=asset_id, brand_id=brand.id)
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        # Capture bytes/metadata before the session closes so the StreamingResponse
        # generator doesn't touch a detached row.
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


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media(asset_id: int, brand=Depends(require_brand)) -> None:
    db = get_session_local()()
    try:
        if not storage.soft_delete(db, asset_id=asset_id, brand_id=brand.id):
            raise HTTPException(status_code=404, detail="Asset not found")
    finally:
        db.close()
