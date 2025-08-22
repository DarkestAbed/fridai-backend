# GPL-3.0-only
import os, pathlib, shutil
from typing import List
from fastapi import APIRouter, Depends, UploadFile, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..dependencies import get_db
from ..models import Task, Attachment
from ..schemas import AttachmentOut

router = APIRouter()

STORAGE_DIR = pathlib.Path(__file__).resolve().parent.parent / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/{task_id}/attachments", response_model=AttachmentOut)
async def add_attachment(task_id: int, file: UploadFile, db: AsyncSession = Depends(get_db)):
    t = (await db.execute(select(Task).where(Task.id==task_id))).scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Task not found")
    safe_name = os.path.basename(file.filename)
    target = STORAGE_DIR / safe_name
    with open(target, "wb") as out:
        shutil.copyfileobj(file.file, out)
    a = Attachment(task_id=t.id, filename=safe_name, url=f"/static/{safe_name}")
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return AttachmentOut.model_validate(a, from_attributes=True)

@router.get("/{task_id}/attachments", response_model=List[AttachmentOut])
async def list_attachments(task_id: int, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Attachment).where(Attachment.task_id==task_id))).scalars().all()
    return [AttachmentOut.model_validate(x, from_attributes=True) for x in rows]
