# app/routers/attachments.py

import aiofiles
import filetype

from fastapi import APIRouter, Depends, UploadFile, HTTPException, Request
from os.path import basename
from pathlib import Path
from re import sub
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import uuid4

from app.dependencies import get_db
from app.limiter import limiter
from app.models import Task, Attachment
from app.schemas import AttachmentOut


router = APIRouter()

CHUNK_SIZE = 256 * 1024  # 256 KiB per read
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

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

# Maps allowed extensions to the set of MIME types filetype may report.
# Extensions with an empty set have no magic bytes (plain text) — skip MIME check.
ALLOWED_MIMES: dict[str, set[str]] = {
    ".jpg":  {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png":  {"image/png"},
    ".gif":  {"image/gif"},
    ".pdf":  {"application/pdf"},
    ".txt":  set(),
    ".doc":  {"application/msword", "application/zip"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/zip"},
    ".xls":  {"application/vnd.ms-excel", "application/zip"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/zip"},
    ".md":   set(),
}

STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def secure_filename(filename: str) -> str:
    """Generate a secure filename preventing path traversal attacks."""
    base_name = basename(filename)
    extension = Path(base_name).suffix.lower()
    # Only keep alphanumeric, dots, underscores, and hyphens
    safe_name = sub(r'[^a-zA-Z0-9._-]', '', base_name)
    if not safe_name or safe_name == extension:
        safe_name = "file"
    unique_name = f"{uuid4()}_{safe_name}"
    return unique_name


@router.post("/{task_id}/attachments", response_model=AttachmentOut)
@limiter.limit("10/minute")
async def add_attachment(
    request: Request,
    task_id: int,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename not provided")

    # Early rejection via Content-Length hint when available
    if file.size is not None and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            400,
            f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )

    # Validate extension before any disk I/O
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            f"File type {file_ext} not allowed. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Validate task exists before writing to disk
    t = (
        (await db.execute(select(Task).where(Task.id == task_id)))
        .scalar_one_or_none()
    )
    if not t:
        raise HTTPException(404, "Task not found")

    # Generate secure path
    safe_name = secure_filename(file.filename)
    target = STORAGE_DIR / safe_name
    try:
        target_resolved = target.resolve()
        storage_resolved = STORAGE_DIR.resolve()
        if not str(target_resolved).startswith(str(storage_resolved)):
            raise HTTPException(400, "Invalid file path")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "Invalid file path")

    # Stream from UploadFile to disk; track size and capture first chunk for MIME check
    accumulated = 0
    first_chunk = None
    try:
        async with aiofiles.open(target, "wb") as out:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                if first_chunk is None:
                    first_chunk = chunk
                accumulated += len(chunk)
                if accumulated > MAX_FILE_SIZE:
                    break
                await out.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        # Clean up partial file on write failure
        target.unlink(missing_ok=True)
        raise HTTPException(500, f"Failed to save file: {exc}")

    # Post-stream size check (handles mid-stream overflow)
    if accumulated > MAX_FILE_SIZE:
        target.unlink(missing_ok=True)
        raise HTTPException(
            400,
            f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )

    # MIME validation using magic bytes from first chunk
    if first_chunk is not None:
        allowed_mimes = ALLOWED_MIMES.get(file_ext, set())
        if allowed_mimes:
            kind = filetype.match(first_chunk)
            if kind is not None and kind.mime not in allowed_mimes:
                target.unlink(missing_ok=True)
                raise HTTPException(
                    400,
                    f"File content does not match declared type '{file_ext}'. "
                    f"Detected: {kind.mime}",
                )

    # Create DB record
    a = Attachment(task_id=t.id, filename=safe_name, url=f"/static/{safe_name}")
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return AttachmentOut.model_validate(a, from_attributes=True)


@router.get("/{task_id}/attachments", response_model=List[AttachmentOut])
@limiter.limit("120/minute")
async def list_attachments(
    request: Request,
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    rows = (
        (
            await db.execute(
                select(Attachment)
                .where(Attachment.task_id == task_id)
            )
        )
        .scalars()
        .all()
    )
    return [
        AttachmentOut.model_validate(x, from_attributes=True)
        for x in rows
    ]
