"""Catalog pack endpoints (Phase 4)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.pack import Pack
from app.schemas.pack import PackOut

router = APIRouter()


@router.get("/packs", response_model=list[PackOut])
async def list_packs(session: AsyncSession = Depends(get_session)) -> list[Pack]:
    rows = await session.scalars(
        select(Pack).where(Pack.is_active.is_(True)).order_by(Pack.created_at)
    )
    return list(rows)


@router.get("/packs/{slug}", response_model=PackOut)
async def get_pack(slug: str, session: AsyncSession = Depends(get_session)) -> Pack:
    pack = await session.scalar(
        select(Pack).where(Pack.slug == slug, Pack.is_active.is_(True))
    )
    if pack is None:
        raise HTTPException(status_code=404, detail="pack not found")
    return pack
