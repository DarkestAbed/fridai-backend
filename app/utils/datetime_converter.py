# app/utils/datetime_converter.py

import pendulum

from datetime import datetime
from pendulum import DateTime as PendulumDT
from typing import Optional


def pendulum_to_datetime(dt: PendulumDT) -> Optional[datetime]:
    """Convert Pendulum DateTime to standard Python datetime."""
    if dt is None:
        return None
    return dt.to_datetime()                                     # type: ignore


def datetime_to_pendulum(dt: datetime, tz: Optional[str] = None) -> Optional[PendulumDT]:
    """Convert standard Python datetime to Pendulum DateTime.

    Args:
        dt: The datetime to convert.
        tz: Timezone string. Defaults to settings_cache.timezone at call time.
    """
    if dt is None:
        return None
    if tz is None:
        from app.utils.tz import get_tz
        tz = get_tz()
    if dt.tzinfo is None:
        # Assume naive datetime is in the configured timezone
        return pendulum.instance(dt, tz=tz)
    return pendulum.instance(dt)


def verify_timestamp(dts: str, tz: Optional[str] = None) -> bool:
    """Verify if input str timestamp is valid in datetime or Pendulum."""
    if dts is None or dts == "None" or dts == "null":
        return True
    if tz is None:
        from app.utils.tz import get_tz
        tz = get_tz()
    error_fg: int = 0
    # pendulum check
    try:
        _ = pendulum.parse(dts, tz=tz)
    except Exception:
        error_fg += 1
    # datetime check
    try:
        _ = datetime.strptime(dts, "%Y-%m-%dT%H:%M:%S.%f")
    except Exception:
        error_fg += 1
    # checking results
    return error_fg < 2
