from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)

from app.database import Base


TARGET_TYPE_URL = "url"
TARGET_TYPE_HANDLE = "handle"
TARGET_TYPE_QUERY = "query"
TARGET_TYPE_PAGE_NAME = "page_name"

ALL_TARGET_TYPES = (
    TARGET_TYPE_URL,
    TARGET_TYPE_HANDLE,
    TARGET_TYPE_QUERY,
    TARGET_TYPE_PAGE_NAME,
)


class CompetitorTargetModel(Base):
    """Per-actor scrape target for a competitor.

    One row per (competitor, actor_key). Stores the input the user wants the
    scraper to run against — Facebook page URL, Instagram handle, website URL,
    Google query, etc. Decouples per-actor inputs from the competitor's display
    name and lets each scraper be configured / disabled / rerun independently.
    """

    __tablename__ = "competitor_targets"
    __table_args__ = (
        UniqueConstraint("competitor_id", "actor_key", name="uq_targets_competitor_actor"),
    )

    id = Column(Integer, primary_key=True, index=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id"), index=True, nullable=False)
    brand_id = Column(Integer, ForeignKey("brands.id"), index=True, nullable=False)

    actor_key = Column(String, nullable=False, index=True)
    target_value = Column(Text, nullable=False)
    target_type = Column(String, nullable=False, default=TARGET_TYPE_QUERY)

    is_enabled = Column(Boolean, nullable=False, default=True)

    last_run_at = Column(DateTime, nullable=True)
    last_cost_usd = Column(Numeric(10, 4), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True, default=None)

    def __repr__(self) -> str:
        return f"<CompetitorTarget competitor={self.competitor_id} actor={self.actor_key} type={self.target_type}>"
