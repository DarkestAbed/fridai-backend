# app/models.py

from __future__ import annotations
from enum import Enum as PyEnum
from pendulum import DateTime as PendulumDT, now
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    ForeignKey,
    String,
    Text,
    Enum as SAEnum,
    DateTime,
    Boolean,
    UniqueConstraint,
)
from typing import List, Optional

from app.db import Base


class StatusEnum(str, PyEnum):
    pending = "pending"
    completed = "completed"


class RelationshipType(str, PyEnum):
    generic = "generic"
    dependency = "dependency"


class TaskTags(Base):
    __tablename__ = "task_tags"
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    tasks: Mapped[List["Task"]] = relationship(
        back_populates="category",
        lazy="selectin",
    )


class Tag(Base):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    tasks: Mapped[List["Task"]] = relationship(
        secondary="task_tags",
        back_populates="tags",
        lazy="selectin",
    )


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text(), default=None)
    status: Mapped[StatusEnum] = mapped_column(
        SAEnum(StatusEnum),
        default=StatusEnum.pending,
    )
    due_at: Mapped[Optional[PendulumDT]] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )
    created_at: Mapped[PendulumDT] = mapped_column(
        DateTime(timezone=True),
        default=lambda: now("America/Santiago"),
        nullable=False,
    )
    updated_at: Mapped[PendulumDT] = mapped_column(
        DateTime(timezone=True),
        default=lambda: now("America/Santiago"),
        onupdate=lambda: now("America/Santiago"),
        nullable=False,
    )
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL")
    )
    category: Mapped[Optional[Category]] = relationship(
        back_populates="tasks",
        lazy="selectin",
    )
    tags: Mapped[List[Tag]] = relationship(
        secondary="task_tags",
        back_populates="tasks",
        lazy="selectin",
    )
    attachments: Mapped[List["Attachment"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Attachment(Base):
    __tablename__ = "attachments"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(Text())
    created_at: Mapped[PendulumDT] = mapped_column(
        DateTime(timezone=True),
        default=lambda: now("America/Santiago"),
        nullable=False,
    )
    task: Mapped[Task] = relationship(
        back_populates="attachments",
        lazy="selectin",
    )


class TaskRelationship(Base):
    __tablename__ = "task_relationships"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        index=True,
    )
    related_task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        index=True,
    )
    rel_type: Mapped[RelationshipType] = mapped_column(
        SAEnum(RelationshipType),
        default=RelationshipType.generic,
    )


class NotificationLog(Base):
    __tablename__ = "notification_logs"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    kind: Mapped[str] = mapped_column(String(50))
    destination: Mapped[str] = mapped_column(String(255))
    payload: Mapped[str] = mapped_column(Text())
    sent_at: Mapped[PendulumDT] = mapped_column(
        DateTime(timezone=True),
        default=lambda: now("America/Santiago"),
        nullable=False,
    )


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
        return [ 
            x.strip()
            for x in (self.apprise_urls or "").splitlines()
            if x.strip()
        ]
