# app/utils/datetime_converter.py

import pendulum

from datetime import datetime
from pendulum import DateTime as PendulumDT
from typing import Optional


def pendulum_to_datetime(dt: PendulumDT) -> Optional[datetime]:
    """Convert Pendulum DateTime to standard Python datetime."""
    if dt is None:
        return None
    # print(f"{dt.to_datetime() = }")                             # type: ignore
    return dt.to_datetime()                                     # type: ignore


def datetime_to_pendulum(dt: datetime) -> Optional[PendulumDT]:
    """Convert standard Python datetime to Pendulum DateTime."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Assume naive datetime is in Santiago timezone
        return pendulum.instance(dt, tz="America/Santiago")
    return pendulum.instance(dt)


def verify_timestamp(dts: str) -> bool:
    """Verify if input str timestamp is valid in datetime or Pendulum"""
    if dts is None or dts == "None" or dts == "null":
        return True
    error_fg: int = 0
    # pendulum check
    try:
        _ = pendulum.parse(dts, tz="America/Santiago")
    except:
        error_fg += 1
    # datetime check
    try:
        _ = datetime.strptime(dts, "%Y-%m-%dT%H:%M:%S.%f")
    except:
        error_fg += 1
    # checking results
    return error_fg < 2
