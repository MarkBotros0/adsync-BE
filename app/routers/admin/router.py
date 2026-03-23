"""Admin-only routes (SUPER role required).

Endpoints:
  GET  /admin/users          – list all users across all brands
  GET  /admin/brands         – list all brands
  POST /admin/brands         – create a new brand
  GET  /admin/brands/{id}/users – list users for a specific brand
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.repositories.brand import BrandRepository
from app.repositories.user import UserRepository
from app.database import get_session_local
from app.dependencies import require_super

router = APIRouter(prefix="/admin", tags=["Admin"])


def _get_user_repo() -> UserRepository:
    db = get_session_local()()
    return UserRepository(db)


def _get_brand_repo() -> BrandRepository:
    db = get_session_local()()
    return BrandRepository(db)


class CreateBrandRequest(BaseModel):
    name: str
    website: str | None = None
    industry: str | None = None
    logo_url: str | None = None


@router.get("/users")
async def list_all_users(_user=Depends(require_super)):
    """Return all users across all brands with their brand info."""
    repo = _get_user_repo()
    try:
        users = repo.get_all_users()
        result = []
        for u in users:
            brand = u.brand  # lazy-load while session open
            _ = brand.subscription if brand else None
            result.append(u.to_dict())
        return {"success": True, "total": len(result), "users": result}
    finally:
        repo.db.close()


@router.get("/brands")
async def list_all_brands(_user=Depends(require_super)):
    """Return all brands with subscription info."""
    repo = _get_brand_repo()
    try:
        brands = repo.get_all_brands()
        for b in brands:
            _ = b.subscription  # eager-load while session open
        return {
            "success": True,
            "total": len(brands),
            "brands": [b.to_dict() for b in brands],
        }
    finally:
        repo.db.close()


@router.post("/brands", status_code=201)
async def create_brand(body: CreateBrandRequest, _user=Depends(require_super)):
    """Create a new brand (SUPER only)."""
    repo = _get_brand_repo()
    try:
        brand = repo.create_brand(
            name=body.name,
            website=body.website,
            industry=body.industry,
            logo_url=body.logo_url,
        )
        _ = brand.subscription
        return {"success": True, "brand": brand.to_dict()}
    finally:
        repo.db.close()


@router.get("/brands/{brand_id}/users")
async def list_brand_users(brand_id: int, _user=Depends(require_super)):
    """List all users for a given brand."""
    brand_repo = _get_brand_repo()
    user_repo = _get_user_repo()
    try:
        brand = brand_repo.get_by_id(brand_id)
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")
        users = user_repo.get_by_brand(brand_id)
        return {
            "success": True,
            "brand": brand.to_dict(),
            "total": len(users),
            "users": [u.to_dict() for u in users],
        }
    finally:
        brand_repo.db.close()
        user_repo.db.close()
