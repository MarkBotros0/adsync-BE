from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from app.database import Base


class SubscriptionModel(Base):
    """Subscription plan database model"""

    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)  # e.g. free, starter, pro
    display_name = Column(String, nullable=False)
    description = Column(String)
    price_monthly = Column(Integer, default=0)   # price in cents
    price_yearly = Column(Integer, default=0)    # price in cents
    features = Column(JSON, nullable=False, default=dict)  # feature flags & limits
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Subscription {self.name}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "price_monthly": self.price_monthly,
            "price_yearly": self.price_yearly,
            "features": self.features,
            "is_active": self.is_active,
        }


# Default subscription plans seeded at startup
DEFAULT_SUBSCRIPTIONS = [
    {
        "name": "free",
        "display_name": "Free",
        "description": "Get started with basic social media monitoring.",
        "price_monthly": 0,
        "price_yearly": 0,
        "features": {
            "max_brands": 1,
            "max_pages": 1,
            "max_ad_accounts": 0,
            "mentions_limit": 500,
            "analytics": False,
            "ai_digest": False,
            "alerts": False,
            "reports": False,
            "team_members": 1,
            "influencer_tracking": False,
            "instagram": False,
            "tiktok": False,
            "export": False,
        },
    },
    {
        "name": "starter",
        "display_name": "Starter",
        "description": "For small brands growing their social presence.",
        "price_monthly": 2900,
        "price_yearly": 29000,
        "features": {
            "max_brands": 3,
            "max_pages": 5,
            "max_ad_accounts": 2,
            "mentions_limit": 5000,
            "analytics": True,
            "ai_digest": False,
            "alerts": True,
            "reports": False,
            "team_members": 3,
            "influencer_tracking": False,
            "instagram": True,
            "tiktok": False,
            "export": True,
        },
    },
    {
        "name": "pro",
        "display_name": "Pro",
        "description": "For growing teams that need full analytics and AI insights.",
        "price_monthly": 7900,
        "price_yearly": 79000,
        "features": {
            "max_brands": 10,
            "max_pages": 20,
            "max_ad_accounts": 10,
            "mentions_limit": 50000,
            "analytics": True,
            "ai_digest": True,
            "alerts": True,
            "reports": True,
            "team_members": 10,
            "influencer_tracking": True,
            "instagram": True,
            "tiktok": True,
            "export": True,
        },
    },
]
