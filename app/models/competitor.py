from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class CompetitorModel(Base):
    """A saved competitor for a brand. Identified by name; we derive search inputs from it."""

    __tablename__ = "competitors"
    __table_args__ = (
        UniqueConstraint("brand_id", "slug", name="uq_competitors_brand_slug"),
    )

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), index=True, nullable=False)

    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True, default=None)

    jobs = relationship(
        "CompetitorAnalysisJobModel",
        back_populates="competitor",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Competitor brand={self.brand_id} name={self.name!r}>"
