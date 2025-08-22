# app/utils/datetime_converter.py

import pendulum

from datetime import datetime
from pendulum import DateTime as PendulumDT


def pendulum_to_datetime(dt: PendulumDT) -> datetime:
    """Convert Pendulum DateTime to standard Python datetime."""
    if dt is None:
        return None
    return dt.to_datetime()


def datetime_to_pendulum(dt: datetime) -> PendulumDT:
    """Convert standard Python datetime to Pendulum DateTime."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Assume naive datetime is in Santiago timezone
        return pendulum.instance(dt, tz="America/Santiago")
    return pendulum.instance(dt)
