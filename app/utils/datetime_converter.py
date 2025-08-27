# app/utils/datetime_converter.py

import pendulum

from datetime import datetime
from pendulum import DateTime as PendulumDT


def pendulum_to_datetime(dt: PendulumDT) -> datetime:
    """Convert Pendulum DateTime to standard Python datetime."""
    if dt is None:
        return None
    # print(f"{dt.to_datetime() = }")                             # type: ignore
    return dt.to_datetime()                                     # type: ignore


def datetime_to_pendulum(dt: datetime) -> PendulumDT:
    """Convert standard Python datetime to Pendulum DateTime."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Assume naive datetime is in Santiago timezone
        # print(f"{pendulum.instance(dt, tz="America/Santiago") = }")
        return pendulum.instance(dt, tz="America/Santiago")
    # print(f"{pendulum.instance(dt) = }")
    return pendulum.instance(dt)


def verify_timestamp(dts: str) -> bool:
    """Verify if input str timestamp is valid in datetime or Pendulum"""
    print(f"{dts = }")
    if dts is None:
        return True
    else:
        error_fg: int = 0
        try:
            # pendulum check
            _ = pendulum.parse(dts, tz="America/Santiago")
            # print(f"Pendulum: {_ = }")
        except:
            print("Not a valid Pendulum timestamp")
            error_fg = +1
        try:
            # datetime check
            _ = datetime.strptime(dts, "%Y-%m-%dT%H:%M:%S.%f")
            # print(f"datetime: {_ = }")
        except:
            print("Not a valid datetime timestamp")
            error_fg =+ 1
        # print(f"{error_fg = }")
        if error_fg == 2:
            return False
        else:
            print("Valid timestamp. Proceeding...")
            return True
