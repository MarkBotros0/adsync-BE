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
from app.repositories.invitation import InvitationRepository
from app.database import get_session_local
from app.dependencies import require_super, require_admin_or_super
from app.models.user import UserRole

router = APIRouter(prefix="/admin", tags=["Admin"])


def _get_user_repo() -> UserRepository:
    db = get_session_local()()
    return UserRepository(db)


def _get_brand_repo() -> BrandRepository:
    db = get_session_local()()
    return BrandRepository(db)


def _get_invite_repo() -> InvitationRepository:
    db = get_session_local()()
    return InvitationRepository(db)


class CreateBrandRequest(BaseModel):
    name: str
    website: str | None = None
    industry: str | None = None
    logo_url: str | None = None


@router.get("/users")
async def list_all_users(_user=Depends(require_super)):
    """Return all users across all brands with their brand memberships."""
    from app.repositories.user_brand import UserBrandRepository
    repo = _get_user_repo()
    try:
        users = repo.get_all_users()
        result = []
        for u in users:
            # Eager-load memberships while session is open
            memberships = u.brand_memberships
            brands = []
            for m in memberships:
                if m.deleted_at is None:
                    b = m.brand
                    if b:
                        brands.append({
                            "id": b.id,
                            "name": b.name,
                            "role": m.role.value if hasattr(m.role, "value") else m.role,
                        })
            user_dict = u.to_dict()
            user_dict["brands"] = brands
            result.append(user_dict)
        return {"success": True, "total": len(result), "users": result}
    finally:
        repo.db.close()


@router.get("/brands")
async def list_all_brands(_user=Depends(require_super)):
    """Return all brands with subscription info."""
    repo = _get_brand_repo()
    try:
        brands = repo.get_all_brands()
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
        return {"success": True, "brand": brand.to_dict()}
    finally:
        repo.db.close()


@router.get("/invitations")
async def list_all_invitations(_user=Depends(require_super)):
    """Return all pending invitations across all brands (SUPER only)."""
    invite_repo = _get_invite_repo()
    try:
        invitations = invite_repo.get_all_invitations()
        for inv in invitations:
            _ = inv.brand  # eager-load while session open
        return {
            "success": True,
            "total": len(invitations),
            "invitations": [inv.to_dict() for inv in invitations],
        }
    finally:
        invite_repo.db.close()


@router.get("/brands/{brand_id}/invitations")
async def list_brand_invitations(brand_id: int, current_user=Depends(require_admin_or_super)):
    """Return pending invitations for a specific brand."""
    role = current_user.role.value if isinstance(current_user.role, UserRole) else current_user.role
    current_brand_id = current_user.brand.id if current_user.brand else None
    if role == UserRole.ADMIN.value and current_brand_id != brand_id:
        raise HTTPException(status_code=403, detail="Access denied to this brand's invitations")

    invite_repo = _get_invite_repo()
    try:
        invitations = invite_repo.get_pending_by_brand(brand_id)
        for inv in invitations:
            _ = inv.brand  # eager-load while session open
        return {
            "success": True,
            "total": len(invitations),
            "invitations": [inv.to_dict() for inv in invitations],
        }
    finally:
        invite_repo.db.close()


@router.get("/brands/{brand_id}/users")
async def list_brand_users(brand_id: int, current_user=Depends(require_admin_or_super)):
    """List all users for a given brand.

    SUPER users can query any brand. ADMIN users can only query their own brand.
    """
    role = current_user.role.value if isinstance(current_user.role, UserRole) else current_user.role
    current_brand_id = current_user.brand.id if current_user.brand else None
    if role == UserRole.ADMIN.value and current_brand_id != brand_id:
        raise HTTPException(status_code=403, detail="Access denied to this brand's users")
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
