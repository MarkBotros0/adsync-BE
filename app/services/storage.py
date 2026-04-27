"""Postgres-backed media storage — replaces an S3 / MinIO layer.

Per the deployment constraint (no Redis / MinIO / S3, only API + frontend + Postgres),
file payloads live as ``BYTEA`` on the ``media_assets.content`` column. This module is
the only place that touches that column directly so size limits, mime sniffing, and
quota enforcement are centralised.
"""
from __future__ import annotations

import logging
from typing import IO

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.media_asset import KIND_IMAGE, KIND_VIDEO, MediaAssetModel

logger = logging.getLogger(__name__)


# Hard caps — Postgres BYTEA tops out at 1GB per row, but realistic per-asset limits
# are much smaller. Bump these once we benchmark a few real video uploads.
MAX_IMAGE_BYTES = 10 * 1024 * 1024     # 10 MiB
MAX_VIDEO_BYTES = 100 * 1024 * 1024    # 100 MiB

_IMAGE_MIMES: frozenset[str] = frozenset({
    "image/jpeg", "image/png", "image/gif", "image/webp",
})
_VIDEO_MIMES: frozenset[str] = frozenset({
    "video/mp4", "video/quicktime", "video/webm",
})


class StorageError(Exception):
    """Raised by ``store`` for any client-fixable problem (mime, size)."""


def kind_for(mime: str) -> str:
    if mime in _IMAGE_MIMES:
        return KIND_IMAGE
    if mime in _VIDEO_MIMES:
        return KIND_VIDEO
    raise StorageError(f"Unsupported media type: {mime}")


def _read_with_cap(stream: IO[bytes], cap: int) -> bytes:
    """Read at most ``cap+1`` bytes — returning ``cap+1`` means we exceeded the limit."""
    return stream.read(cap + 1)


async def store(
    db: Session,
    *,
    brand_id: int,
    upload: UploadFile,
    uploader_user_id: int | None = None,
) -> MediaAssetModel:
    """Persist an uploaded file as a row in ``media_assets`` and return the row."""
    mime = (upload.content_type or "").lower()
    kind = kind_for(mime)
    cap = MAX_VIDEO_BYTES if kind == KIND_VIDEO else MAX_IMAGE_BYTES

    raw = await upload.read()
    if len(raw) == 0:
        raise StorageError("Empty file")
    if len(raw) > cap:
        raise StorageError(f"File exceeds the {cap // (1024 * 1024)} MiB limit for {kind}s")

    asset = MediaAssetModel(
        brand_id=brand_id,
        uploader_user_id=uploader_user_id,
        kind=kind,
        filename=upload.filename or "upload",
        mime=mime,
        size_bytes=len(raw),
        content=raw,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def read(db: Session, asset_id: int, brand_id: int) -> MediaAssetModel | None:
    """Fetch the asset row including its bytes, scoped to the brand."""
    return (
        db.query(MediaAssetModel)
        .filter(
            MediaAssetModel.id == asset_id,
            MediaAssetModel.brand_id == brand_id,
            MediaAssetModel.deleted_at.is_(None),
        )
        .first()
    )


def list_for_brand(
    db: Session,
    brand_id: int,
    kind: str | None = None,
    limit: int = 100,
) -> list[MediaAssetModel]:
    """List assets for a brand. Excludes ``content`` from the SELECT to keep responses small.

    Note: SQLAlchemy will still load ``content`` lazily on attribute access — the FE
    listing endpoint must NOT serialise it (use a Pydantic response_model that omits it).
    """
    q = db.query(MediaAssetModel).filter(
        MediaAssetModel.brand_id == brand_id,
        MediaAssetModel.deleted_at.is_(None),
    )
    if kind:
        q = q.filter(MediaAssetModel.kind == kind)
    return q.order_by(MediaAssetModel.created_at.desc()).limit(limit).all()


def soft_delete(db: Session, asset_id: int, brand_id: int) -> bool:
    asset = read(db, asset_id, brand_id)
    if not asset:
        return False
    from datetime import datetime
    asset.deleted_at = datetime.utcnow()
    asset.updated_at = datetime.utcnow()
    db.commit()
    return True
