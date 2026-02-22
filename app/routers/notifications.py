# app/routers/notifications.py

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.limiter import limiter
from app.models import NotificationLog, NotificationTemplate
from app.schemas import TemplatePatch
from app.services.notifications import (
    _send_all,
    trigger_due_soon,
    trigger_overdue,
)


router = APIRouter()


@router.post("/cron")
@limiter.limit("5/minute")
async def cron(
    request: Request,
    mode: str = Query("both", pattern="^(near_due|overdue|both)$"),
    db: AsyncSession = Depends(get_db),
):
    sent = 0
    if mode in ("near_due", "both"):
        sent += await trigger_due_soon(db)
    if mode in ("overdue", "both"):
        sent += await trigger_overdue(db)
    return {"sent": sent}


@router.post("/test")
@limiter.limit("5/minute")
async def test_message(request: Request, db: AsyncSession = Depends(get_db)):
    payload = "# Test notification\nThis is a test."
    urls = await _send_all(payload, "Test")
    return {"destinations": urls}


@router.get("/logs")
@limiter.limit("120/minute")
async def list_logs(request: Request, limit: int = 50, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(NotificationLog)
        .order_by(NotificationLog.sent_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [
        dict(
            id=r.id,
            task_id=r.task_id,
            kind=r.kind,
            destination=r.destination,
            sent_at=r.sent_at
        )
        for r in rows
    ]


@router.get("/templates/{key}")
@limiter.limit("120/minute")
async def get_template(request: Request, key: str, db: AsyncSession = Depends(get_db)):
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
        return {"key": key, "markdown": ""}
    return {"key": row.key, "markdown": row.markdown}


@router.patch("/templates/{key}")
@limiter.limit("30/minute")
async def patch_template(
    request: Request,
    key: str,
    body: TemplatePatch,
    db: AsyncSession = Depends(get_db),
):
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
        row = NotificationTemplate(key=key, markdown=body.markdown)
        db.add(row)
    else:
        row.markdown = body.markdown
    await db.commit()
    return {"ok": True}
