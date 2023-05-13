from datetime import datetime
from typing import Union, cast

import icalendar  # type: ignore
import pytz


def single(u: Union[int, float]) -> str:
    return "" if u == 1 else "s"


def humanize(seconds: Union[float, int]) -> str:
    """
    Convert seconds to human format:

    3600 -> in 1 hour
    1800 -> in 30 minutes
    -40 -> 40 seconds ago
    """
    if seconds == 0:
        return "now"

    human_delta = ""

    future = True if seconds > 0 else False

    seconds = abs(seconds)

    if seconds >= 3600:
        hours = seconds // 3600
        human_delta = f"{int(hours)} hour{single(hours)}"

    elif seconds >= 60:
        minutes = seconds // 60
        human_delta = f"{int(minutes)} minute{single(minutes)}"

    else:
        human_delta = f"{int(seconds)} second{single(seconds)}"

    return f"in {human_delta}" if future else f"{human_delta} ago"


def get_event_dt(
    event: icalendar.Event, tzinfo: pytz.BaseTzInfo, obj: str = "DTSTART"
) -> datetime:
    dtstart = event[obj].dt

    # convert date to datetime starting at midnight
    if not isinstance(dtstart, datetime):
        dtstart = datetime.combine(dtstart, datetime.min.time())

    return cast(datetime, dtstart.replace(tzinfo=tzinfo))
