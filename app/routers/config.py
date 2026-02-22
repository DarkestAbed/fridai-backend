# app/routers/config.py

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.limiter import limiter
from app.models import AppSettings
from app.schemas import SettingsOut, SettingsPatch
from app.settings import settings_cache


router = APIRouter()


@router.get("", response_model=SettingsOut)
@limiter.limit("120/minute")
async def get_config(request: Request, db: AsyncSession = Depends(get_db)):
    await settings_cache.load(db)
    return SettingsOut(**settings_cache.to_dict())


@router.patch("")
@limiter.limit("30/minute")
async def patch_config(request: Request, body: SettingsPatch, db: AsyncSession = Depends(get_db)):
    row = (
        (await db.execute(select(AppSettings).where(AppSettings.id==1)))
        .scalar_one_or_none()
    )
    if not row:
        row = AppSettings(id=1)
        db.add(row)
    row.timezone = body.timezone
    row.theme = body.theme
    row.notifications_enabled = body.notifications_enabled
    row.near_due_hours = body.near_due_hours
    row.scheduler_interval_seconds = body.scheduler_interval_seconds
    row.ntfy_topics = body.ntfy_topics
    row.language = body.language
    await db.commit()
    await settings_cache.load(db)  # hot reload runtime
    return {"ok": True, "settings": settings_cache.to_dict()}
