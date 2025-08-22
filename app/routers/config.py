# GPL-3.0-only
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..dependencies import get_db
from ..models import AppSettings
from ..schemas import SettingsOut, SettingsPatch
from ..settings import settings_cache

router = APIRouter()

@router.get("", response_model=SettingsOut)
async def get_config(db: AsyncSession = Depends(get_db)):
    await settings_cache.load(db)
    return SettingsOut(**settings_cache.to_dict())

@router.patch("")
async def patch_config(body: SettingsPatch, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(AppSettings).where(AppSettings.id==1))).scalar_one_or_none()
    if not row:
        row = AppSettings(id=1)
        db.add(row)
    row.timezone = body.timezone
    row.theme = body.theme
    row.notifications_enabled = body.notifications_enabled
    row.near_due_hours = body.near_due_hours
    row.scheduler_interval_seconds = body.scheduler_interval_seconds
    row.apprise_urls = body.apprise_urls
    await db.commit()
    await settings_cache.load(db)  # hot reload runtime
    return {"ok": True, "settings": settings_cache.to_dict()}
