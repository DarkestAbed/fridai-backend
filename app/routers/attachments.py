# app/routers/attachments.py

from fastapi import APIRouter, Depends, UploadFile, HTTPException
from os.path import basename
from pathlib import Path
from shutil import copyfileobj
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import uuid4

from app.dependencies import get_db
from app.models import Task, Attachment
from app.schemas import AttachmentOut


router = APIRouter()

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".pdf",
    ".txt",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
}
MAX_FILE_SIZE = 50 * 1024 * 1024
STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/{task_id}/attachments", response_model=AttachmentOut)
async def add_attachment(
    task_id: int,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(
            status_code=404,
            detail="Filename not provided"
        )
    # Validate file size
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large")
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "File type not allowed")
    t = (
        (await db.execute(select(Task).where(Task.id==task_id)))
        .scalar_one_or_none()
    )
    if not t:
        raise HTTPException(404, "Task not found")
    safe_name = f"{uuid4()}-{basename(file.filename)}"
    target = STORAGE_DIR / safe_name
    with open(target, "wb") as out:
        copyfileobj(file.file, out)
    a = Attachment(task_id=t.id, filename=safe_name, url=f"/static/{safe_name}")
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return AttachmentOut.model_validate(a, from_attributes=True)


@router.get("/{task_id}/attachments", response_model=List[AttachmentOut])
async def list_attachments(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    rows = (
        (
            await db.execute(
                select(Attachment)
                .where(Attachment.task_id==task_id)
            )
        )
        .scalars()
        .all()
    )
    return [ 
        AttachmentOut.model_validate(x, from_attributes=True)
        for x in rows
    ]
