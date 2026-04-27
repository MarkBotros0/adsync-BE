"""Client-view router — agencies invite their end clients to read-only pages of a brand."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.database import get_session_local
from app.dependencies import require_brand
from app.models.client_view import ClientViewModel
from app.repositories.user import UserRepository

router = APIRouter(prefix="/brands/client-views", tags=["Brand Client Views"])


_ALLOWED_PAGES = frozenset({"analytics", "reports", "content"})


class ClientViewCreate(BaseModel):
    email: EmailStr
    allowed_pages: list[str] = Field(default_factory=lambda: ["analytics", "reports"])


class ClientViewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    brand_id: int
    user_id: int
    allowed_pages_json: list[str]


@router.get("", response_model=list[ClientViewResponse])
async def list_client_views(brand=Depends(require_brand)) -> Any:
    db = get_session_local()()
    try:
        return (
            db.query(ClientViewModel)
            .filter(
                ClientViewModel.brand_id == brand.id,
                ClientViewModel.deleted_at.is_(None),
            )
            .all()
        )
    finally:
        db.close()


@router.post("", response_model=ClientViewResponse, status_code=status.HTTP_201_CREATED)
async def create_client_view(payload: ClientViewCreate, brand=Depends(require_brand)) -> Any:
    """Grant the user with ``email`` read-only access to ``allowed_pages`` on this brand.

    The user must already exist (invited via the standard org-invite flow). This
    endpoint is the page-allow-list, not the user-creation step.
    """
    bad = [p for p in payload.allowed_pages if p not in _ALLOWED_PAGES]
    if bad:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported pages: {bad}. Allowed: {sorted(_ALLOWED_PAGES)}",
        )
    db = get_session_local()()
    try:
        user = UserRepository(db).get_by_email(payload.email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found — invite them first")
        existing = (
            db.query(ClientViewModel)
            .filter(
                ClientViewModel.brand_id == brand.id,
                ClientViewModel.user_id == user.id,
                ClientViewModel.deleted_at.is_(None),
            )
            .first()
        )
        if existing:
            existing.allowed_pages_json = payload.allowed_pages
            db.commit()
            db.refresh(existing)
            return existing
        row = ClientViewModel(
            brand_id=brand.id,
            user_id=user.id,
            invited_by_user_id=getattr(brand, "owner_user_id", None),
            allowed_pages_json=payload.allowed_pages,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    finally:
        db.close()


@router.delete("/{client_view_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client_view(client_view_id: int, brand=Depends(require_brand)) -> None:
    db = get_session_local()()
    try:
        row = (
            db.query(ClientViewModel)
            .filter(
                ClientViewModel.id == client_view_id,
                ClientViewModel.brand_id == brand.id,
                ClientViewModel.deleted_at.is_(None),
            )
            .first()
        )
        if not row:
            raise HTTPException(status_code=404, detail="Client view not found")
        row.deleted_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()
