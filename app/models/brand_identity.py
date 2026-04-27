"""Per-brand visual identity — drives white-labelled reports + the dashboard chrome."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, LargeBinary, String, UniqueConstraint

from app.database import Base


class BrandIdentityModel(Base):
    """Brand's logo (bytes), colours, font family, and white-label subdomain.

    One row per brand (UNIQUE on brand_id). Used by the reports generator for the PDF
    header and by the FE for theming when an agency client logs into a client_view.
    """

    __tablename__ = "brand_identities"
    __table_args__ = (
        UniqueConstraint("brand_id", name="uq_brand_identities_brand"),
    )

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False, index=True)

    logo_bytes = Column(LargeBinary, nullable=True)
    logo_mime = Column(String, nullable=True)
    logo_filename = Column(String, nullable=True)

    primary_color = Column(String, nullable=False, default="#6366f1")
    secondary_color = Column(String, nullable=False, default="#0ea5e9")
    font_family = Column(String, nullable=False, default="Inter")

    white_label_subdomain = Column(String, nullable=True, index=True, unique=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True, default=None)
