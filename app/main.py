# GPL-3.0-only
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db import init_models, enable_sqlite_wal
from .routers import tasks, categories, tags, relationships, attachments, views, notifications, config
from .settings import settings_cache

app = FastAPI(title="Tasks Platform API", version="2.0.0-vibe")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # single-user demo; tighten if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    await enable_sqlite_wal()
    await init_models()
    await settings_cache.load()

# Routers
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(categories.router, prefix="/api/categories", tags=["categories"])
app.include_router(tags.router, prefix="/api/tags", tags=["tags"])
app.include_router(relationships.router, prefix="/api/relationships", tags=["relationships"])
app.include_router(attachments.router, prefix="/api/tasks", tags=["attachments"])
app.include_router(views.router, prefix="/api/views", tags=["views"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(config.router, prefix="/api/config", tags=["config"])

@app.get("/healthz")
async def healthz():
    return {"ok": True, "version": "2.0.0-vibe"}
