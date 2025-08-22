# GPL-3.0-only
from __future__ import annotations
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, String, Text, Enum, Table, DateTime, Boolean, UniqueConstraint
from .db import Base
import enum

class StatusEnum(str, enum.Enum):
    pending = "pending"
    completed = "completed"

task_tags = Table(
    "task_tags",
    Base.metadata,
    mapped_column("task_id", ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    mapped_column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    tasks: Mapped[List["Task"]] = relationship(back_populates="category")

class Tag(Base):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    tasks: Mapped[List["Task"]] = relationship(secondary=task_tags, back_populates="tags")

class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text(), default=None)
    status: Mapped[StatusEnum] = mapped_column(Enum(StatusEnum), default=StatusEnum.pending)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))
    category: Mapped[Optional[Category]] = relationship(back_populates="tasks")
    tags: Mapped[List[Tag]] = relationship(secondary=task_tags, back_populates="tasks")
    attachments: Mapped[List["Attachment"]] = relationship(back_populates="task", cascade="all, delete-orphan")

class Attachment(Base):
    __tablename__ = "attachments"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    task: Mapped[Task] = relationship(back_populates="attachments")

class RelationshipType(str, enum.Enum):
    generic = "generic"
    dependency = "dependency"

class TaskRelationship(Base):
    __tablename__ = "task_relationships"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    related_task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    rel_type: Mapped[RelationshipType] = mapped_column(Enum(RelationshipType), default=RelationshipType.generic)

class NotificationLog(Base):
    __tablename__ = "notification_logs"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tasks.id", ondelete="SET NULL"), index=True, nullable=True)
    kind: Mapped[str] = mapped_column(String(50))
    destination: Mapped[str] = mapped_column(String(255))
    payload: Mapped[str] = mapped_column(Text())
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

class NotificationTemplate(Base):
    __tablename__ = "notification_templates"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    markdown: Mapped[str] = mapped_column(Text())

class AppSettings(Base):
    __tablename__ = "app_settings"
    __table_args__ = (UniqueConstraint("id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    theme: Mapped[str] = mapped_column(String(32), default="light")
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    near_due_hours: Mapped[int] = mapped_column(default=24)
    scheduler_interval_seconds: Mapped[int] = mapped_column(default=60)
    apprise_urls: Mapped[str] = mapped_column(Text(), default="")

    def apprise_list(self) -> list[str]:
        return [x.strip() for x in (self.apprise_urls or "").splitlines() if x.strip()]
