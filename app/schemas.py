# app/schemas.py

from __future__ import annotations
from datetime import datetime
from pydantic import (
    BaseModel,
    ConfigDict,
    model_validator,
    field_validator,
    constr,
)
from re import search, IGNORECASE, DOTALL
from typing import Optional, List

from app.models import StatusEnum, RelationshipType


class ExtendedBase(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)


# ----- Task -----
class TaskCreate(ExtendedBase):
    title: constr(min_length=1, max_length=200, strip_whitespace=True)
    description: Optional[constr(max_length=5000, strip_whitespace=True)] = None
    due_at: Optional[datetime] = None
    category_id: Optional[int] = None
    tag_ids: Optional[List[int]] = None
    
    @field_validator('title')
    def validate_title(cls, v):
        if not v or v.isspace():
            raise ValueError('Title cannot be empty or only whitespace')
        # Remove any potential HTML/script tags
        if search(r'<[^>]*>', v):
            raise ValueError('Title cannot contain HTML tags')
        return v
    
    @field_validator('description')
    def validate_description(cls, v):
        if v is not None:
            # Remove any potential script tags
            if search(r'<script[^>]*>.*?</script>', v, IGNORECASE | DOTALL):
                raise ValueError('Description cannot contain script tags')
        return v
    
    @field_validator('category_id')
    def validate_category_id(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Category ID must be positive')
        return v
    
    @field_validator('tag_ids')
    def validate_tag_ids(cls, v):
        if v is not None:
            if len(v) > 50:  # Reasonable limit on tags per task
                raise ValueError('Too many tags (maximum 50)')
            if any(tag_id <= 0 for tag_id in v):
                raise ValueError('All tag IDs must be positive')
            if len(set(v)) != len(v):
                raise ValueError('Duplicate tag IDs not allowed')
        return v


class TaskOut(ExtendedBase):
    id: int
    title: str
    description: Optional[str]
    status: StatusEnum
    due_at: Optional[datetime]
    category_id: Optional[int]
    tag_ids: List[int] = []

    @model_validator(mode='before')
    @classmethod
    def extract_tag_ids(cls, data):
        if hasattr(data, 'tags') and data.tags is not None:
            data.tag_ids = [ tag.id for tag in data.tags ]
        return data

    class Config:
        from_attributes = True


class TaskPatchDescription(ExtendedBase):
    description: Optional[str] = None


class TaskPatchDue(ExtendedBase):
    due_at: Optional[datetime] = None


class AddTags(ExtendedBase):
    tag_ids: List[int]


# ----- Category/Tag -----
class CategoryCreate(BaseModel):
    name: constr(min_length=1, max_length=100, strip_whitespace=True)
    
    @field_validator('name')
    def validate_name(cls, v):
        if not v or v.isspace():
            raise ValueError('Category name cannot be empty')
        if search(r'<[^>]*>', v):
            raise ValueError('Category name cannot contain HTML tags')
        return v


class CategoryOut(ExtendedBase):
    id: int
    name: str
    class Config:
        from_attributes = True


class TagCreate(BaseModel):
    name: constr(min_length=1, max_length=100, strip_whitespace=True)
    
    @field_validator('name')
    def validate_name(cls, v):
        if not v or v.isspace():
            raise ValueError('Tag name cannot be empty')
        if search(r'<[^>]*>', v):
            raise ValueError('Tag name cannot contain HTML tags')
        return v


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
    created_at: datetime
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
    timezone: str = "America/Santiago"
    theme: str = "light"
    notifications_enabled: bool = True
    near_due_hours: int = 24
    scheduler_interval_seconds: int = 60
    apprise_urls: str = ""
