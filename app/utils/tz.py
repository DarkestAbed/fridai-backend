# app/utils/tz.py


def get_tz() -> str:
    """Return the current runtime timezone from settings_cache.

    Uses a lazy import to avoid circular imports:
      models.py -> db.py
      settings.py -> models.py, db.py
      utils/tz.py -> settings.py  (safe: settings does not import tz.py)
    """
    from app.settings import settings_cache
    return settings_cache.timezone
