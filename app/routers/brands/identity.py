"""Brand-identity router — logo + colours + white-label subdomain.

Logo is uploaded as multipart and stored inline as BYTEA on ``brand_identities``;
served back via ``GET /brands/{id}/identity/logo``. Used by the reports PDF header
and (later) the FE chrome when a client_view user signs in.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from app.database import get_session_local
from app.dependencies import require_brand
from app.models.brand_identity import BrandIdentityModel

router = APIRouter(prefix="/brands/identity", tags=["Brand Identity"])


class IdentityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    brand_id: int
    primary_color: str
    secondary_color: str
    font_family: str
    white_label_subdomain: str | None = None
    has_logo: bool = False


def _to_response(row: BrandIdentityModel) -> IdentityResponse:
    return IdentityResponse(
        id=row.id,
        brand_id=row.brand_id,
        primary_color=row.primary_color,
        secondary_color=row.secondary_color,
        font_family=row.font_family,
        white_label_subdomain=row.white_label_subdomain,
        has_logo=bool(row.logo_bytes),
    )


@router.get("", response_model=IdentityResponse)
async def get_identity(brand=Depends(require_brand)) -> Any:
    """Get the current brand's identity. Auto-creates a default row if missing."""
    db = get_session_local()()
    try:
        row = (
            db.query(BrandIdentityModel)
            .filter(
                BrandIdentityModel.brand_id == brand.id,
                BrandIdentityModel.deleted_at.is_(None),
            )
            .first()
        )
        if not row:
            row = BrandIdentityModel(brand_id=brand.id)
            db.add(row)
            db.commit()
            db.refresh(row)
        return _to_response(row)
    finally:
        db.close()


@router.put("", response_model=IdentityResponse)
async def update_identity(
    brand=Depends(require_brand),
    primary_color: str | None = Form(None),
    secondary_color: str | None = Form(None),
    font_family: str | None = Form(None),
    white_label_subdomain: str | None = Form(None),
    logo: UploadFile | None = File(None),
) -> Any:
    """Update colours / font / subdomain and optionally replace the logo bytes."""
    db = get_session_local()()
    try:
        row = (
            db.query(BrandIdentityModel)
            .filter(
                BrandIdentityModel.brand_id == brand.id,
                BrandIdentityModel.deleted_at.is_(None),
            )
            .first()
        )
        if not row:
            row = BrandIdentityModel(brand_id=brand.id)
            db.add(row)

        if primary_color is not None:
            row.primary_color = primary_color
        if secondary_color is not None:
            row.secondary_color = secondary_color
        if font_family is not None:
            row.font_family = font_family
        if white_label_subdomain is not None:
            row.white_label_subdomain = white_label_subdomain or None

        if logo is not None:
            data = await logo.read()
            if not data:
                raise HTTPException(status_code=422, detail="Empty logo file")
            if len(data) > 2 * 1024 * 1024:
                raise HTTPException(status_code=422, detail="Logo must be smaller than 2 MiB")
            row.logo_bytes = data
            row.logo_mime = logo.content_type or "image/png"
            row.logo_filename = logo.filename or "logo"

        row.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(row)
        return _to_response(row)
    finally:
        db.close()


@router.get("/logo")
async def stream_logo(brand=Depends(require_brand)) -> Any:
    """Stream the brand's logo bytes back to the client."""
    db = get_session_local()()
    try:
        row = (
            db.query(BrandIdentityModel)
            .filter(
                BrandIdentityModel.brand_id == brand.id,
                BrandIdentityModel.deleted_at.is_(None),
            )
            .first()
        )
        if not row or not row.logo_bytes:
            raise HTTPException(status_code=404, detail="No logo set for this brand")
        bytes_, mime, filename = row.logo_bytes, row.logo_mime or "image/png", row.logo_filename or "logo"
    finally:
        db.close()

    return StreamingResponse(
        iter([bytes_]),
        media_type=mime,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
