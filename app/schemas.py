# GPL-3.0-only
from __future__ import annotations
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from .models import StatusEnum, RelationshipType

# ----- Task -----
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_at: Optional[datetime] = None
    category_id: Optional[int] = None
    tag_ids: Optional[List[int]] = None

class TaskOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: StatusEnum
    due_at: Optional[datetime]
    category_id: Optional[int]
    tag_ids: List[int] = []
    class Config:
        from_attributes = True

class TaskPatchDescription(BaseModel):
    description: Optional[str] = None

class TaskPatchDue(BaseModel):
    due_at: Optional[datetime] = None

class AddTags(BaseModel):
    tag_ids: List[int]

# ----- Category/Tag -----
class CategoryCreate(BaseModel):
    name: str

class CategoryOut(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

class TagCreate(BaseModel):
    name: str

class TagOut(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

# ----- Relationships -----
class RelationshipCreate(BaseModel):
    task_id: int
    related_task_id: int
    rel_type: RelationshipType

# ----- Attachments -----
class AttachmentOut(BaseModel):
    id: int
    filename: str
    url: str
    created_at: datetime
    class Config:
        from_attributes = True

# ----- Views / Summaries -----
class CountItem(BaseModel):
    key: str
    count: int

# ----- Notifications -----
class TemplatePatch(BaseModel):
    markdown: str

# ----- Settings -----
class SettingsOut(BaseModel):
    timezone: str = "UTC"
    theme: str = "light"
    notifications_enabled: bool = True
    near_due_hours: int = 24
    scheduler_interval_seconds: int = 60
    apprise_urls: str = ""

class SettingsPatch(SettingsOut):
    pass
