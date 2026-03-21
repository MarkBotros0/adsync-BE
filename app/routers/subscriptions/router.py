"""Subscription plan routes.

Endpoints:
  GET  /subscriptions          – list all active plans
  GET  /subscriptions/{name}   – get a specific plan by name
"""
from fastapi import APIRouter, HTTPException
from app.repositories.subscription import SubscriptionRepository
from app.database import get_session_local

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


def _get_repo():
    SessionLocal = get_session_local()
    db = SessionLocal()
    return SubscriptionRepository(db)


@router.get("")
def list_subscriptions():
    """Return all active subscription plans with their features."""
    repo = _get_repo()
    try:
        plans = repo.get_active()
        return {
            "success": True,
            "subscriptions": [p.to_dict() for p in plans],
        }
    finally:
        repo.db.close()


@router.get("/{name}")
def get_subscription(name: str):
    """Return a single subscription plan by name (e.g. free, starter, pro, enterprise)."""
    repo = _get_repo()
    try:
        plan = repo.get_by_name(name)
        if not plan or not plan.is_active:
            raise HTTPException(status_code=404, detail=f"Subscription plan '{name}' not found")
        return {"success": True, "subscription": plan.to_dict()}
    finally:
        repo.db.close()
