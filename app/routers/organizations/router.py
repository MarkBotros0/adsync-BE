"""Organization management routes.

Endpoints:
  GET  /organizations/me               – get current user's organization
  POST /organizations/brands           – create a brand within the org
  GET  /organizations/brands           – list all brands in the org
  PATCH /organizations/brands/{id}     – update a brand
  DELETE /organizations/brands/{id}    – soft-delete a brand
  GET  /organizations/members          – list org admins
  POST /organizations/members          – add an org admin
  DELETE /organizations/members/{uid}  – remove an org admin
"""
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.database import get_session_local
from app.dependencies import require_org_admin, require_super, optional_org_id
from app.models.user import UserRole
from app.repositories.brand import BrandRepository
from app.repositories.organization import OrganizationRepository
from app.repositories.organization_membership import OrganizationMembershipRepository
from app.repositories.subscription import SubscriptionRepository
from app.repositories.user import UserRepository

router = APIRouter(prefix="/organizations", tags=["Organizations"])
logger = logging.getLogger(__name__)


def _get_org_repo() -> OrganizationRepository:
    return OrganizationRepository(get_session_local()())


def _get_brand_repo() -> BrandRepository:
    return BrandRepository(get_session_local()())


def _get_org_membership_repo() -> OrganizationMembershipRepository:
    return OrganizationMembershipRepository(get_session_local()())


def _get_user_repo() -> UserRepository:
    return UserRepository(get_session_local()())


# ──────────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────────

class CreateBrandRequest(BaseModel):
    name: str
    logo_url: str | None = None
    website: str | None = None
    industry: str | None = None


class UpdateBrandRequest(BaseModel):
    name: str | None = None
    logo_url: str | None = None
    website: str | None = None
    industry: str | None = None


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────

@router.get("/me")
async def get_my_org(current_user=Depends(require_org_admin)):
    """Return the current user's organization details."""
    org_id = getattr(current_user, "org_id", 0)
    org_repo = _get_org_repo()
    try:
        org = org_repo.get_by_id(org_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        _ = org.subscription
        brand_count = org_repo.count_active_brands(org_id)
        max_brands = org.subscription.features.get("max_brands", 1) if org.subscription else 1
        return {
            "success": True,
            "organization": {
                **org.to_dict(),
                "brand_count": brand_count,
                "max_brands": max_brands,
            },
        }
    finally:
        org_repo.db.close()


@router.post("/brands", status_code=201)
async def create_brand(body: CreateBrandRequest, current_user=Depends(require_org_admin)):
    """Create a new brand within the organization. Enforces subscription brand limit."""
    org_id = getattr(current_user, "org_id", 0)
    org_repo = _get_org_repo()
    brand_repo = _get_brand_repo()

    try:
        org = org_repo.get_by_id(org_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        _ = org.subscription

        # Enforce brand limit
        if org.subscription:
            max_brands = org.subscription.features.get("max_brands", 1)
            if max_brands != -1:
                current_count = org_repo.count_active_brands(org_id)
                if current_count >= max_brands:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Brand limit reached ({max_brands}). Upgrade your subscription to add more brands.",
                    )

        brand = brand_repo.create_brand(
            name=body.name,
            organization_id=org_id,
            logo_url=body.logo_url,
            website=body.website,
            industry=body.industry,
        )
        return {"success": True, "brand": brand.to_dict()}
    finally:
        org_repo.db.close()
        brand_repo.db.close()


@router.get("/brands")
async def list_brands(current_user=Depends(require_org_admin)):
    """List all brands in the organization."""
    org_id = getattr(current_user, "org_id", 0)
    brand_repo = _get_brand_repo()
    try:
        brands = brand_repo.get_brands_for_org(org_id)
        return {
            "success": True,
            "total": len(brands),
            "brands": [b.to_dict() for b in brands],
        }
    finally:
        brand_repo.db.close()


@router.patch("/brands/{brand_id}", status_code=200)
async def update_brand(brand_id: int, body: UpdateBrandRequest, current_user=Depends(require_org_admin)):
    """Update brand details. ORG_ADMIN can only update brands in their org."""
    org_id = getattr(current_user, "org_id", 0)
    current_role = current_user.role.value if isinstance(current_user.role, UserRole) else current_user.role
    brand_repo = _get_brand_repo()

    try:
        brand = brand_repo.get_by_id(brand_id)
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")
        if current_role == UserRole.ORG_ADMIN.value and brand.organization_id != org_id:
            raise HTTPException(status_code=403, detail="Brand does not belong to your organization")

        if body.name is not None:
            brand.name = body.name
        if body.logo_url is not None:
            brand.logo_url = body.logo_url
        if body.website is not None:
            brand.website = body.website
        if body.industry is not None:
            brand.industry = body.industry
        brand.updated_at = datetime.utcnow()
        brand_repo.update(brand)
        return {"success": True, "brand": brand.to_dict()}
    finally:
        brand_repo.db.close()


@router.delete("/brands/{brand_id}", status_code=200)
async def delete_brand(brand_id: int, current_user=Depends(require_org_admin)):
    """Soft-delete a brand."""
    org_id = getattr(current_user, "org_id", 0)
    current_role = current_user.role.value if isinstance(current_user.role, UserRole) else current_user.role
    brand_repo = _get_brand_repo()

    try:
        brand = brand_repo.get_by_id(brand_id)
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")
        if current_role == UserRole.ORG_ADMIN.value and brand.organization_id != org_id:
            raise HTTPException(status_code=403, detail="Brand does not belong to your organization")

        brand_repo.soft_delete(brand_id)
        return {"success": True, "message": "Brand deleted"}
    finally:
        brand_repo.db.close()


@router.get("/members")
async def list_members(current_user=Depends(require_org_admin)):
    """List all ORG_ADMIN members of the organization."""
    org_id = getattr(current_user, "org_id", 0)
    org_membership_repo = _get_org_membership_repo()
    user_repo = _get_user_repo()

    try:
        memberships = org_membership_repo.get_admins_for_org(org_id)
        result = []
        for m in memberships:
            user = user_repo.get_by_id(m.user_id)
            if user:
                result.append({
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "is_active": user.is_active,
                    "joined_at": m.created_at.isoformat(),
                })
        return {"success": True, "total": len(result), "members": result}
    finally:
        org_membership_repo.db.close()
        user_repo.db.close()
