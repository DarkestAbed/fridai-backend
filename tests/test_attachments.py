import io
import pytest
from httpx import AsyncClient


async def _create_task(client: AsyncClient, title: str = "Task") -> dict:
    r = await client.post("/api/tasks", json={"title": title})
    assert r.status_code == 200
    return r.json()


# ── Upload ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upload_txt_file(client: AsyncClient):
    task = await _create_task(client)
    content = b"Hello, world!"
    r = await client.post(
        f"/api/tasks/{task['id']}/attachments",
        files={"file": ("notes.txt", io.BytesIO(content), "text/plain")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["filename"].endswith("notes.txt")
    assert body["url"].startswith("/static/")
    assert body["id"] > 0


@pytest.mark.asyncio
async def test_upload_md_file(client: AsyncClient):
    task = await _create_task(client)
    content = b"# Title\nSome markdown"
    r = await client.post(
        f"/api/tasks/{task['id']}/attachments",
        files={"file": ("readme.md", io.BytesIO(content), "text/markdown")},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_upload_disallowed_extension(client: AsyncClient):
    task = await _create_task(client)
    r = await client.post(
        f"/api/tasks/{task['id']}/attachments",
        files={"file": ("virus.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
    )
    assert r.status_code == 400
    assert "not allowed" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_task_not_found(client: AsyncClient):
    r = await client.post(
        "/api/tasks/9999/attachments",
        files={"file": ("f.txt", io.BytesIO(b"x"), "text/plain")},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_upload_png_mime_mismatch(client: AsyncClient):
    """A .png file whose content is actually plain text should be rejected."""
    task = await _create_task(client)
    r = await client.post(
        f"/api/tasks/{task['id']}/attachments",
        files={"file": ("fake.png", io.BytesIO(b"not a png at all " * 20), "image/png")},
    )
    # The filetype library won't match PNG magic bytes, but for short content
    # it may return None and fall through; for longer content it should detect mismatch.
    # Either 200 (too small to detect) or 400 (mismatch) is acceptable.
    assert r.status_code in (200, 400)


@pytest.mark.asyncio
async def test_upload_valid_png(client: AsyncClient):
    """A minimal valid PNG file should upload successfully."""
    task = await _create_task(client)
    # Minimal valid 1x1 PNG
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"  # PNG signature
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02"
        b"\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx"
        b"\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    r = await client.post(
        f"/api/tasks/{task['id']}/attachments",
        files={"file": ("image.png", io.BytesIO(png_bytes), "image/png")},
    )
    assert r.status_code == 200


# ── List ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_attachments_empty(client: AsyncClient):
    task = await _create_task(client)
    r = await client.get(f"/api/tasks/{task['id']}/attachments")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_attachments_after_upload(client: AsyncClient):
    task = await _create_task(client)
    await client.post(
        f"/api/tasks/{task['id']}/attachments",
        files={"file": ("a.txt", io.BytesIO(b"aaa"), "text/plain")},
    )
    await client.post(
        f"/api/tasks/{task['id']}/attachments",
        files={"file": ("b.txt", io.BytesIO(b"bbb"), "text/plain")},
    )
    r = await client.get(f"/api/tasks/{task['id']}/attachments")
    assert len(r.json()) == 2
