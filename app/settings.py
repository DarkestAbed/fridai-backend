# GPL-3.0-only
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import AppSettings
from app.db import SessionLocal

@dataclass
class SettingsCache:
    timezone: str = "UTC"
    theme: str = "light"
    notifications_enabled: bool = True
    near_due_hours: int = 24
    scheduler_interval_seconds: int = 60
    apprise_urls: str = ""

    async def load(self, session: Optional[AsyncSession] = None):
        own = False
        if session is None:
            own = True
            session = SessionLocal()
        try:
            res = await session.execute(select(AppSettings).where(AppSettings.id==1))
            obj = res.scalar_one_or_none()
            if not obj:
                obj = AppSettings(id=1)
                session.add(obj)
                await session.commit()
            self.timezone = obj.timezone
            self.theme = obj.theme
            self.notifications_enabled = obj.notifications_enabled
            self.near_due_hours = obj.near_due_hours
            self.scheduler_interval_seconds = obj.scheduler_interval_seconds
            self.apprise_urls = obj.apprise_urls
        finally:
            if own:
                await session.close()

    def to_dict(self):
        return dict(
            timezone=self.timezone,
            theme=self.theme,
            notifications_enabled=self.notifications_enabled,
            near_due_hours=self.near_due_hours,
            scheduler_interval_seconds=self.scheduler_interval_seconds,
            apprise_urls=self.apprise_urls,
        )

settings_cache = SettingsCache()
