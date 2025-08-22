# GPL-3.0-only

from __future__ import annotations
from pendulum import DateTime as PDateTime
from pydantic import BaseModel, ConfigDict
from typing import Optional, List

from app.models import StatusEnum, RelationshipType


class ExtendedBase(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)


# ----- Task -----
class TaskCreate(ExtendedBase):
    title: str
    description: Optional[str] = None
    due_at: Optional[PDateTime] = None
    category_id: Optional[int] = None
    tag_ids: Optional[List[int]] = None


class TaskOut(ExtendedBase):
    id: int
    title: str
    description: Optional[str]
    status: StatusEnum
    due_at: Optional[PDateTime]
    category_id: Optional[int]
    tag_ids: List[int] = []
    class Config:
        from_attributes = True


class TaskPatchDescription(ExtendedBase):
    description: Optional[str] = None


class TaskPatchDue(ExtendedBase):
    due_at: Optional[PDateTime] = None


class AddTags(ExtendedBase):
    tag_ids: List[int]


# ----- Category/Tag -----
class CategoryCreate(ExtendedBase):
    name: str


class CategoryOut(ExtendedBase):
    id: int
    name: str
    class Config:
        from_attributes = True


class TagCreate(ExtendedBase):
    name: str


class TagOut(ExtendedBase):
    id: int
    name: str
    class Config:
        from_attributes = True


# ----- Relationships -----
class RelationshipCreate(ExtendedBase):
    task_id: int
    related_task_id: int
    rel_type: RelationshipType


# ----- Attachments -----
class AttachmentOut(ExtendedBase):
    id: int
    filename: str
    url: str
    created_at: PDateTime
    class Config:
        from_attributes = True


# ----- Views / Summaries -----
class CountItem(ExtendedBase):
    key: str
    count: int


# ----- Notifications -----
class TemplatePatch(ExtendedBase):
    markdown: str


# ----- Settings -----
class SettingsOut(ExtendedBase):
    timezone: str = "America/Santiago"
    theme: str = "light"
    notifications_enabled: bool = True
    near_due_hours: int = 24
    scheduler_interval_seconds: int = 60
    apprise_urls: str = ""


class SettingsPatch(ExtendedBase):
    pass
