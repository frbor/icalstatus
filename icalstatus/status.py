#!/usr/bin/env python3
"""Statusbar ics calendar"""

import html
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import caep
import icalendar  # type: ignore
import pytz
import recurring_ical_events  # type: ignore
import requests

# from dateutil import rrule
from pydantic import BaseModel, Field
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

from icalstatus.date import get_event_dt, humanize

disable_warnings(InsecureRequestWarning)


@dataclass
class Event:
    name: str
    begin: str
    alert: bool


class Config(BaseModel):
    calendar_url: str = Field(description="URI for ICS Calendar")
    timezone: str = Field("CET", description="Timezone (default=CET)")
    no_verify: bool = Field(False, description="Ignore SSL verification errors")
    proxy: Optional[str] = Field(description="Proxy for ICS url")

    all: bool = Field(False, description="Include events that are not today")

    humanize_after_sec: int = Field(
        3600,
        description="Humanize meeting date if less than "
        "this many seconds until meeting",
    )

    alert_sec_before: int = Field(
        300,
        description="Alert meeting at specified seconds before start. "
        "This will switch class for output on waybar.",
    )


def get_data(url: str, no_verify: bool, proxy_string: Optional[str]) -> str:
    """Read the ics file from remote URL"""

    proxies = {"http": proxy_string, "https": proxy_string} if proxy_string else None

    req = requests.get(url, timeout=10, verify=(not no_verify), proxies=proxies)

    return req.text


def get_next_datetime(
    recurring_event: icalendar.Event, now: datetime, tzinfo: pytz.BaseTzInfo
) -> Optional[datetime]:
    begin = None
    for event in recurring_ical_events.of(recurring_event).between(
        now - timedelta(minutes=5), now + timedelta(days=7)
    ):
        begin = get_event_dt(event, tzinfo)

    return begin


def ics_next_event(
    ics_data: str, now: datetime, tzinfo: pytz.BaseTzInfo
) -> Optional[icalendar.Event]:
    curr = None
    diff = None

    cal = icalendar.Calendar.from_ical(ics_data)

    event = None
    for event in cal.walk():
        if not event.name == "VEVENT":
            continue

        begin = get_event_dt(event, tzinfo)

        if begin < now:
            if event.get("RRULE"):
                nextrule = get_next_datetime(event, now, tzinfo)
                if not nextrule:
                    continue

                if nextrule < now:
                    continue
                thisdiff = nextrule - now
                if not curr or thisdiff < diff:
                    diff = thisdiff
                    curr = event
            continue

        thisdiff = begin - now

        if not curr or (diff and (thisdiff < diff)):
            diff = thisdiff
            curr = event

    return curr


def upcoming_event() -> Optional[Event]:
    """Get the next event closest in time"""

    config: Config = caep.load(Config, "ICAL Status", "icalstatus", "config", "status")

    # now = arrow.now().replace(tzinfo=config.timezone)
    tzinfo = pytz.timezone(config.timezone)
    now = datetime.now().replace(tzinfo=tzinfo)
    next = ics_next_event(
        get_data(config.calendar_url, config.no_verify, config.proxy),
        now,
        tzinfo,
    )

    if not next:
        return None

    begin = get_event_dt(next, tzinfo)

    if (now.date() != begin.date()) and not config.all:
        return None

    # If meeteing is soon to begin or we have chosen to include
    # meetings for the next days+, show time in "human format", e.g. `in 5 minutes`
    if (now + timedelta(seconds=config.humanize_after_sec) > begin) or (
        now.date() != begin.date()
    ):
        begin_str = humanize(begin.timestamp() - now.timestamp())
    else:
        begin_str = f"@{begin.strftime('%H:%M')}"

    return Event(
        name=next.get("SUMMARY", "Unknown").strip(),
        begin=begin_str,
        alert=now + timedelta(seconds=config.alert_sec_before) > begin,
    )


def status() -> None:
    """main"""

    event = upcoming_event()

    if not event:
        return

    print(f"{event.name} {event.begin}")


def waybar() -> None:
    event = upcoming_event()

    if not event:
        return

    print(
        json.dumps(
            {
                "text": html.escape(f"{event.name} {event.begin}"),
                "class": "alert" if event.alert else "normal",
            }
        )
    )
    try:
        sys.stdout.flush()
    except BrokenPipeError:
        pass


if __name__ == "__main__":
    status()
