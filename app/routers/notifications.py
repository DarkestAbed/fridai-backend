# GPL-3.0-only
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..dependencies import get_db
from ..models import NotificationLog, NotificationTemplate
from ..schemas import TemplatePatch
from ..services.notifications import trigger_due_soon, trigger_overdue

router = APIRouter()

@router.post("/cron")
async def cron(mode: str = Query("both", pattern="^(near_due|overdue|both)$"), db: AsyncSession = Depends(get_db)):
    sent = 0
    if mode in ("near_due", "both"):
        sent += await trigger_due_soon(db)
    if mode in ("overdue", "both"):
        sent += await trigger_overdue(db)
    return {"sent": sent}

@router.post("/test")
async def test_message(db: AsyncSession = Depends(get_db)):
    from ..services.notifications import _send_all
    payload = "# Test notification\nThis is a test."
    urls = await _send_all(payload, "Test")
    return {"destinations": urls}

@router.get("/logs")
async def list_logs(limit: int = 50, db: AsyncSession = Depends(get_db)):
    stmt = select(NotificationLog).order_by(NotificationLog.sent_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return [dict(id=r.id, task_id=r.task_id, kind=r.kind, destination=r.destination, sent_at=r.sent_at) for r in rows]

@router.get("/templates/{key}")
async def get_template(key: str, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(NotificationTemplate).where(NotificationTemplate.key==key))).scalar_one_or_none()
    if not row:
        return {"key": key, "markdown": ""}
    return {"key": row.key, "markdown": row.markdown}

@router.patch("/templates/{key}")
async def patch_template(key: str, body: TemplatePatch, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(NotificationTemplate).where(NotificationTemplate.key==key))).scalar_one_or_none()
    if not row:
        from ..models import NotificationTemplate as NT
        row = NT(key=key, markdown=body.markdown)
        db.add(row)
    else:
        row.markdown = body.markdown
    await db.commit()
    return {"ok": True}
