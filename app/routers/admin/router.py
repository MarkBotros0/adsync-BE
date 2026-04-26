"""Admin-only routes (SUPER role required).

Endpoints:
  GET    /admin/users                              – list all users across all brands
  GET    /admin/brands                             – list all brands
  POST   /admin/brands                             – create a new brand
  GET    /admin/brands/{id}/users                  – list users for a specific brand
  PATCH  /admin/users/{id}/role                    – change a user's role (NORMAL ↔ ORG_ADMIN)
  POST   /admin/users/{id}/force-signout           – rotate target's session_key
  DELETE /admin/users/{id}                         – remove a user from the org
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.repositories.brand import BrandRepository
from app.repositories.user import UserRepository
from app.repositories.user_brand import UserBrandRepository
from app.repositories.organization_membership import OrganizationMembershipRepository
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


def _get_user_brand_repo() -> UserBrandRepository:
    return UserBrandRepository(get_session_local()())


def _get_org_membership_repo() -> OrganizationMembershipRepository:
    return OrganizationMembershipRepository(get_session_local()())


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
    """Return pending invitations for a specific brand (includes org-level ORG_ADMIN invites)."""
    role = current_user.role.value if isinstance(current_user.role, UserRole) else current_user.role
    current_brand_id = current_user.brand.id if current_user.brand else None
    if role == UserRole.ADMIN.value and current_brand_id != brand_id:
        raise HTTPException(status_code=403, detail="Access denied to this brand's invitations")

    brand_repo = _get_brand_repo()
    invite_repo = _get_invite_repo()
    try:
        brand = brand_repo.get_by_id(brand_id)
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")

        brand_invitations = invite_repo.get_pending_by_brand(brand_id)
        org_invitations = (
            invite_repo.get_pending_by_org(brand.organization_id)
            if brand.organization_id
            else []
        )
        invitations = brand_invitations + org_invitations
        for inv in invitations:
            _ = inv.brand  # eager-load while session open
        return {
            "success": True,
            "total": len(invitations),
            "invitations": [inv.to_dict() for inv in invitations],
        }
    finally:
        brand_repo.db.close()
        invite_repo.db.close()


@router.get("/brands/{brand_id}/users")
async def list_brand_users(brand_id: int, current_user=Depends(require_admin_or_super)):
    """List all users for a given brand — both NORMAL members and the org's ORG_ADMINs.

    SUPER users can query any brand. ADMIN/ORG_ADMIN users can only query their own brand.
    """
    role = current_user.role.value if isinstance(current_user.role, UserRole) else current_user.role
    current_brand_id = current_user.brand.id if current_user.brand else None
    if role == UserRole.ADMIN.value and current_brand_id != brand_id:
        raise HTTPException(status_code=403, detail="Access denied to this brand's users")
    brand_repo = _get_brand_repo()
    user_repo = _get_user_repo()
    om_repo = _get_org_membership_repo()
    try:
        brand = brand_repo.get_by_id(brand_id)
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")

        normal_users = user_repo.get_by_brand(brand_id)
        results: list[dict] = []
        seen_ids: set[int] = set()
        for u in normal_users:
            d = u.to_dict()
            d["effective_role"] = UserRole.NORMAL.value
            results.append(d)
            seen_ids.add(u.id)

        if brand.organization_id:
            admin_memberships = om_repo.get_admins_for_org(brand.organization_id)
            for m in admin_memberships:
                if m.user_id in seen_ids:
                    continue
                admin_user = user_repo.get_by_id(m.user_id)
                if not admin_user or admin_user.deleted_at is not None or not admin_user.is_active:
                    continue
                d = admin_user.to_dict()
                d["effective_role"] = UserRole.ORG_ADMIN.value
                results.append(d)
                seen_ids.add(admin_user.id)

        return {
            "success": True,
            "brand": brand.to_dict(),
            "total": len(results),
            "users": results,
        }
    finally:
        brand_repo.db.close()
        user_repo.db.close()
        om_repo.db.close()


# ── User management (role change / force sign-out / remove) ──────────────────


class UpdateUserRoleRequest(BaseModel):
    role: str  # "NORMAL" or "ORG_ADMIN"


def _caller_org_id(current_user) -> int:
    org_id = getattr(current_user, "org_id", 0) or 0
    if not org_id and current_user.brand and getattr(current_user.brand, "organization_id", None):
        org_id = current_user.brand.organization_id
    return int(org_id or 0)


def _is_caller_super(current_user) -> bool:
    role = current_user.role.value if isinstance(current_user.role, UserRole) else current_user.role
    return role == UserRole.SUPER.value


def _assert_same_org_or_super(current_user, target_user_id: int, om_repo: OrganizationMembershipRepository, ub_repo: UserBrandRepository) -> int:
    """Return the org_id the target belongs to (in shared with the caller). Raises 403/404 otherwise.

    SUPER bypasses org check and returns 0.
    """
    if _is_caller_super(current_user):
        return 0

    caller_org_id = _caller_org_id(current_user)
    if not caller_org_id:
        raise HTTPException(status_code=403, detail="Caller is not associated with an organization")

    # Target is ORG_ADMIN of caller's org?
    if om_repo.get_membership(target_user_id, caller_org_id):
        return caller_org_id

    # Target is a NORMAL member of any brand in the caller's org?
    target_memberships = ub_repo.get_brands_for_user(target_user_id)
    for m in target_memberships:
        b = m.brand
        if b and b.organization_id == caller_org_id:
            return caller_org_id

    raise HTTPException(status_code=404, detail="User not found in your organization")


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    body: UpdateUserRoleRequest,
    current_user=Depends(require_admin_or_super),
):
    """Promote a NORMAL user to ORG_ADMIN, or demote an ORG_ADMIN to NORMAL.

    Demotion lands the user as a NORMAL member of the caller's currently active brand.
    """
    new_role = body.role.upper()
    if new_role not in (UserRole.NORMAL.value, UserRole.ORG_ADMIN.value):
        raise HTTPException(status_code=422, detail="Role must be NORMAL or ORG_ADMIN")

    if not _is_caller_super(current_user) and current_user.id == user_id:
        raise HTTPException(status_code=403, detail="You cannot change your own role")

    user_repo = _get_user_repo()
    om_repo = _get_org_membership_repo()
    ub_repo = _get_user_brand_repo()
    try:
        target = user_repo.get_by_id(user_id)
        if not target or target.deleted_at is not None:
            raise HTTPException(status_code=404, detail="User not found")

        org_id = _assert_same_org_or_super(current_user, user_id, om_repo, ub_repo)
        if not org_id:
            # SUPER caller: derive org from target's first membership
            target_memberships = ub_repo.get_brands_for_user(user_id)
            if target_memberships and target_memberships[0].brand:
                org_id = target_memberships[0].brand.organization_id or 0
            if not org_id:
                target_org = om_repo.get_orgs_for_user(user_id)
                if target_org:
                    org_id = target_org[0].organization_id
            if not org_id:
                raise HTTPException(status_code=400, detail="Cannot determine target organization")

        is_org_admin = om_repo.get_membership(user_id, org_id) is not None
        current_effective = UserRole.ORG_ADMIN.value if is_org_admin else UserRole.NORMAL.value

        if current_effective == new_role:
            return {"success": True, "message": "Role unchanged", "user_id": user_id, "role": new_role}

        if new_role == UserRole.ORG_ADMIN.value:
            # Promote: add org membership, drop brand memberships within this org
            om_repo.create_membership(user_id=user_id, org_id=org_id)
            for m in ub_repo.get_brands_for_user(user_id):
                if m.brand and m.brand.organization_id == org_id:
                    ub_repo.soft_delete(m.id)
        else:
            # Demote: ensure not the last admin
            remaining_admins = [m for m in om_repo.get_admins_for_org(org_id) if m.user_id != user_id]
            if not remaining_admins:
                raise HTTPException(status_code=409, detail="Cannot demote the last admin of the organization")
            om_repo.remove_membership(user_id, org_id)
            # Land them as a NORMAL member of the caller's current brand (if any)
            target_brand_id = current_user.brand.id if (current_user.brand and getattr(current_user.brand, "id", 0)) else None
            if target_brand_id and not ub_repo.get_membership(user_id, target_brand_id):
                from app.models.user_brand import BrandMembershipRole
                ub_repo.create_membership(user_id=user_id, brand_id=target_brand_id, role=BrandMembershipRole.NORMAL)

        # Force the user to re-login so their JWT picks up the new role
        user_repo.rotate_session_key(target)

        return {"success": True, "user_id": user_id, "role": new_role}
    finally:
        user_repo.db.close()
        om_repo.db.close()
        ub_repo.db.close()


@router.post("/users/{user_id}/force-signout", status_code=200)
async def force_signout_user(user_id: int, current_user=Depends(require_admin_or_super)):
    """Rotate the target user's session_key, invalidating all of their JWTs."""
    if not _is_caller_super(current_user) and current_user.id == user_id:
        raise HTTPException(status_code=403, detail="Use /brands/force-signout to sign yourself out")

    user_repo = _get_user_repo()
    om_repo = _get_org_membership_repo()
    ub_repo = _get_user_brand_repo()
    try:
        target = user_repo.get_by_id(user_id)
        if not target or target.deleted_at is not None:
            raise HTTPException(status_code=404, detail="User not found")
        _assert_same_org_or_super(current_user, user_id, om_repo, ub_repo)
        user_repo.rotate_session_key(target)
        return {"success": True, "message": "User has been signed out", "user_id": user_id}
    finally:
        user_repo.db.close()
        om_repo.db.close()
        ub_repo.db.close()


@router.delete("/users/{user_id}", status_code=200)
async def remove_user(user_id: int, current_user=Depends(require_admin_or_super)):
    """Remove a user from the caller's organization.

    Soft-deletes their org membership (if any) and brand memberships within the caller's org,
    then rotates their session_key so any active sessions are invalidated.
    The user account row is preserved (soft-delete is per-membership) so cross-org access remains intact.
    """
    if not _is_caller_super(current_user) and current_user.id == user_id:
        raise HTTPException(status_code=403, detail="You cannot remove yourself")

    user_repo = _get_user_repo()
    om_repo = _get_org_membership_repo()
    ub_repo = _get_user_brand_repo()
    try:
        target = user_repo.get_by_id(user_id)
        if not target or target.deleted_at is not None:
            raise HTTPException(status_code=404, detail="User not found")

        org_id = _assert_same_org_or_super(current_user, user_id, om_repo, ub_repo)
        if not org_id:
            target_memberships = ub_repo.get_brands_for_user(user_id)
            if target_memberships and target_memberships[0].brand:
                org_id = target_memberships[0].brand.organization_id or 0
            if not org_id:
                target_org = om_repo.get_orgs_for_user(user_id)
                if target_org:
                    org_id = target_org[0].organization_id
            if not org_id:
                raise HTTPException(status_code=400, detail="Cannot determine target organization")

        # Last-admin protection
        admin_membership = om_repo.get_membership(user_id, org_id)
        if admin_membership:
            remaining = [m for m in om_repo.get_admins_for_org(org_id) if m.user_id != user_id]
            if not remaining:
                raise HTTPException(status_code=409, detail="Cannot remove the last admin of the organization")
            om_repo.remove_membership(user_id, org_id)

        for m in ub_repo.get_brands_for_user(user_id):
            if m.brand and m.brand.organization_id == org_id:
                ub_repo.soft_delete(m.id)

        user_repo.rotate_session_key(target)

        return {"success": True, "message": "User removed from organization", "user_id": user_id}
    finally:
        user_repo.db.close()
        om_repo.db.close()
        ub_repo.db.close()
