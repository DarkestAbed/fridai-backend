# app/routers/attachments.py

from fastapi import APIRouter, Depends, UploadFile, HTTPException
from os.path import basename
from pathlib import Path
from re import sub
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
    ".md",
}
MAX_FILE_SIZE = 50 * 1024 * 1024
STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def secure_filename(filename: str) -> str:
    """Generate a secure filename preventing path traversal attacks."""
    # Extract the base filename
    base_name = basename(filename)
    # Get file extension
    extension = Path(base_name).suffix.lower()
    # Remove any potentially dangerous characters from filename
    # Only keep alphanumeric, dots, underscores, and hyphens
    safe_name = sub(r'[^a-zA-Z0-9._-]', '', base_name)
    # If filename is empty after sanitization, use a default
    if not safe_name or safe_name == extension:
        safe_name = "file"
    # Generate unique filename with UUID
    unique_name = f"{uuid4()}_{safe_name}"
    return unique_name


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
    # Read file content to check actual size
    content = await file.read()
    await file.seek(0)  # Reset file pointer
    # Validate actual file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            400,
            f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            f"File type {file_ext} not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    # check the tasks exists
    t = (
        (await db.execute(select(Task).where(Task.id==task_id)))
        .scalar_one_or_none()
    )
    if not t:
        raise HTTPException(404, "Task not found")
    # generate secure file name
    safe_name = secure_filename(file.filename)
    target = STORAGE_DIR / safe_name
    # Verify the final path is within STORAGE_DIR (defense in depth)
    try:
        target_resolved = target.resolve()
        storage_resolved = STORAGE_DIR.resolve()
        if not str(target_resolved).startswith(str(storage_resolved)):
            raise HTTPException(400, "Invalid file path")
    except Exception:
        raise HTTPException(400, "Invalid file path")
    # save with context manager for proper cleanup
    try:
        with open(target, "wb") as out:
            copyfileobj(file.file, out)
    except Exception as e:
        raise HTTPException(500, f"Failed to save file: {str(e)}")
    # create db record
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
