# app/services/notifications.py

from __future__ import annotations
import math

import httpx
import pendulum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models import Task, NotificationLog, NotificationTemplate
from app.settings import settings_cache


DEFAULT_DUE_SOON = """
# ⏰ Task due soon: {task_title}
- Due at: {due_at}
- Remaining: {remaining}
"""
DEFAULT_OVERDUE = """
# ❗ Task overdue: {task_title}
- Was due at: {due_at}
- Overdue by: {overdue_by}
"""


async def _get_template(db: AsyncSession, key: str, default: str) -> str:
    row = (
        (
            await db.execute(
                select(NotificationTemplate)
                .where(NotificationTemplate.key==key)
            )
        )
        .scalar_one_or_none()
    )
    if not row:
        row = NotificationTemplate(key=key, markdown=default)
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row.markdown


def _render(template: str, **kw) -> str:
    return template.format(**kw)


async def _send_all(payload: str, subject: str):
    topics = [
        u.strip()
        for u in (settings_cache.ntfy_topics or "").splitlines()
        if u.strip()
    ]
    if not topics or not settings_cache.notifications_enabled:
        return []
    sent = []
    async with httpx.AsyncClient(timeout=10) as client:
        for topic_url in topics:
            resp = await client.post(
                topic_url,
                content=payload,
                headers={
                    "Title": subject,
                    "Markdown": "yes",
                    "Priority": "default",
                },
            )
            resp.raise_for_status()
            sent.append(topic_url)
    return sent


async def trigger_due_soon(db: AsyncSession) -> int:
    hours = settings_cache.near_due_hours or 24
    horizon = func.datetime(func.now(), f"+{hours} hours")
    # Only get tasks that haven't been notified recently
    subquery = (
        select(NotificationLog.task_id)
        .where(
            NotificationLog.kind == "due_soon",
            NotificationLog.sent_at >= func.datetime(func.now(), "-1 day"),
        )
    )
    stmt = (
        select(Task)
        .where(
            Task.status != "completed",
            Task.due_at.is_not(None),
            Task.due_at <= horizon,
            Task.due_at >= func.now(),
            Task.id.not_in(subquery),       # Exclude recently notified tasks
        )
    )
    tasks = (await db.execute(stmt)).scalars().all()
    tmpl = await _get_template(db, "due_soon", DEFAULT_DUE_SOON)
    sent = 0
    tz = settings_cache.timezone or "UTC"
    now = pendulum.now(tz)
    for t in tasks:
        due = t.due_at
        if due and due.tzinfo is None:
            due = pendulum.instance(due, tz=tz)
        remaining_seconds = (due - now).total_seconds() if due else 0
        remaining_hours = math.ceil(remaining_seconds / 3600)
        payload = _render(
            tmpl,
            task_title=t.title,
            due_at=t.due_at,
            remaining=f"{remaining_hours}h",
        )
        urls = await _send_all(payload, subject="Task due soon")
        for dest in urls:
            db.add(
                NotificationLog(
                    task_id=t.id,
                    destination=dest,
                    kind="due_soon",
                    payload=payload,
                )
            )
            sent += 1
    await db.commit()
    return sent


async def trigger_overdue(db: AsyncSession) -> int:
    # Skip tasks already notified as overdue in the last hour
    recently_notified = (
        select(NotificationLog.task_id)
        .where(
            NotificationLog.kind == "overdue",
            NotificationLog.sent_at >= func.datetime(func.now(), "-1 hour"),
        )
    )
    stmt = (
        select(Task)
        .where(
            Task.status!="completed",
            Task.due_at.is_not(None),
            Task.due_at < func.now(),
            Task.id.not_in(recently_notified),
        )
    )
    tasks = (await db.execute(stmt)).scalars().all()
    tmpl = await _get_template(db, "overdue", DEFAULT_OVERDUE)
    sent = 0
    tz = settings_cache.timezone or "UTC"
    now = pendulum.now(tz)
    for t in tasks:
        due = t.due_at
        if due and due.tzinfo is None:
            due = pendulum.instance(due, tz=tz)
        overdue_seconds = (now - due).total_seconds() if due else 0
        overdue_hours = math.ceil(overdue_seconds / 3600)
        payload = _render(
            tmpl,
            task_title=t.title,
            due_at=t.due_at,
            overdue_by=f"{overdue_hours}h",
        )
        urls = await _send_all(payload, subject="Task overdue")
        for dest in urls:
            db.add(
                NotificationLog(
                    task_id=t.id,
                    destination=dest,
                    kind="overdue",
                    payload=payload,
                )
            )
            sent += 1
    await db.commit()
    return sent
