# Backend

FastAPI + SQLAlchemy 2.0 (async) over SQLite. No auth (single user).

## Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Notes
- DB file stored at `/app/data/app.db` (via Compose volume).
- Attachments stored under `/app/app/storage/`.
- Uses Apprise for notifications.
