# app/settings.py

from __future__ import annotations
from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict, Optional

from app.models import AppSettings
from app.db import SessionLocal


@dataclass
class SettingsCache:
    timezone: str = "UTC"
    theme: str = "light"
    notifications_enabled: bool = True
    near_due_hours: int = 24
    scheduler_interval_seconds: int = 60
    ntfy_topics: str = ""
    language: str = "en"

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
            self.ntfy_topics = obj.ntfy_topics
            self.language = obj.language
        finally:
            if own:
                await session.close()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timezone": str(self.timezone),
            "theme": str(self.theme),
            "notifications_enabled": bool(self.notifications_enabled),
            "near_due_hours": int(self.near_due_hours),
            "scheduler_interval_seconds": int(self.scheduler_interval_seconds),
            "ntfy_topics": str(self.ntfy_topics),
            "language": str(self.language),
        }

settings_cache = SettingsCache()
