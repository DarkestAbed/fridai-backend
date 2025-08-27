# app/services/notifications.py

from __future__ import annotations
from apprise import Apprise
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
    urls = [ 
        u 
        for u in (settings_cache.apprise_urls or "").splitlines()
        if u.strip()
    ]
    if not urls or not settings_cache.notifications_enabled:
        return []
    app = Apprise()
    for u in urls:
        app.add(u.strip())
    await app.async_notify(body=payload, title=subject)
    return urls


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
    for t in tasks:
        payload = _render(
            tmpl,
            task_title=t.title,
            due_at=t.due_at,
            remaining="<= %sh" % hours,
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
    stmt = (
        select(Task)
        .where(
            Task.status!="completed",
            Task.due_at.is_not(None),
            Task.due_at < func.now(),
        )
    )
    tasks = (await db.execute(stmt)).scalars().all()
    tmpl = await _get_template(db, "overdue", DEFAULT_OVERDUE)
    sent = 0
    for t in tasks:
        payload = _render(
            tmpl,
            task_title=t.title,
            due_at=t.due_at,
            overdue_by=">0h",
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
