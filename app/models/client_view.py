"""Read-only view granted to an agency's end client on a single brand."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class ClientViewModel(Base):
    """Lets an ORG_ADMIN invite a client (their customer) to view selected pages of a brand.

    The user is still authenticated through the normal user table; the row simply
    declares "this user is allowed to see these pages on this brand, in read-only".
    Allowed pages live as a string list in ``allowed_pages_json``
    (e.g. ``["analytics", "reports"]``).
    """

    __tablename__ = "client_views"
    __table_args__ = (
        UniqueConstraint("brand_id", "user_id", name="uq_client_views_brand_user"),
    )

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    invited_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    allowed_pages_json = Column(JSONB, nullable=False, default=list)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True, default=None)
