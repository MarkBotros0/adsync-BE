"""Media asset stored INLINE in Postgres as BYTEA (no S3, per deployment constraint)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, LargeBinary, String

from app.database import Base


KIND_IMAGE = "image"
KIND_VIDEO = "video"


class MediaAssetModel(Base):
    """Image or video asset uploaded by a brand user, stored inline in Postgres.

    No external object store. The composer references assets by ID; the publisher
    loop reads ``content`` and either base64-uploads or temp-files it before sending
    to the platform API.
    """

    __tablename__ = "media_assets"

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), index=True, nullable=False)
    uploader_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    kind = Column(String, nullable=False)  # KIND_IMAGE | KIND_VIDEO
    filename = Column(String, nullable=False)
    mime = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False, default=0)
    content = Column(LargeBinary, nullable=False)  # the actual file payload

    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True, default=None)
