#!/usr/bin/env python3
"""Statusbar ics calendar"""

import html
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import caep
import icalendar  # type: ignore
import recurring_ical_events  # type: ignore
import requests
from pydantic import BaseModel, Field
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

from . import retry
from .date import get_event_dt, humanize

disable_warnings(InsecureRequestWarning)


class CalendarParseError(Exception): ...


@dataclass
class Event:
    name: str
    begin: str
    alert: bool


class Config(BaseModel):
    calendar_url: str = Field(description="URI for ICS Calendar")
    timezone: str = Field("CET", description="Timezone (default=CET)")
    no_verify: bool = Field(False, description="Ignore SSL verification errors")
    proxy: str | None = Field(description="Proxy for ICS url")

    all: bool = Field(description="Include events that are not today")
    debug: bool = Field(description="Add debug output")

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


def remove_non_printable(value: str) -> str:
    return "".join(i for i in value if i.isprintable())


def get_data(url: str, no_verify: bool, proxy_string: str | None) -> str:
    """Read the ics file from remote URL"""

    proxies = {"http": proxy_string, "https": proxy_string} if proxy_string else None

    req = requests.get(url, timeout=10, verify=(not no_verify), proxies=proxies)

    return req.text


def get_next_datetime(
    recurring_event: icalendar.Event, now: datetime, tzinfo: ZoneInfo
) -> datetime | None:
    begin = None
    for event in recurring_ical_events.of(recurring_event).between(
        now - timedelta(minutes=5), now + timedelta(days=7)
    ):
        # for event in recurring_ical_events.of(recurring_event).after(now):
        begin = get_event_dt(event, tzinfo)

    return begin


def debug(config: Config, message: str) -> None:
    if not config.debug:
        return

    print(f"DEBUG: {message}")


def ics_next_event(
    ics_data: str, now: datetime, tzinfo: ZoneInfo
) -> tuple[datetime | None, icalendar.Event | None]:
    curr = None
    diff = None
    next_dt: datetime | None = None

    try:
        cal = icalendar.Calendar.from_ical(ics_data)
    except ValueError as e:
        raise CalendarParseError(e) from e

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
                if (not diff) or (not curr) or (thisdiff < diff):
                    diff = thisdiff
                    curr = event
                    next_dt = nextrule
            continue

        thisdiff = begin - now

        if not curr or (diff and (thisdiff < diff)):
            diff = thisdiff
            curr = event
            next_dt = begin

    return next_dt, curr


def upcoming_event() -> Event | None:
    """Get the next event closest in time"""

    config: Config = caep.load(Config, "ICAL Status", "icalstatus", "config", "status")

    tzinfo = ZoneInfo(config.timezone)
    now = datetime.now().replace(tzinfo=tzinfo)

    next_dt, next_event = retry.retry(
        ics_next_event,  # type: ignore
        args=[
            get_data(config.calendar_url, config.no_verify, config.proxy),
            now,
            tzinfo,
        ],
        exception_classes=(
            ConnectionError,
            TimeoutError,
            CalendarParseError,
        ),
    )
    if (not next_event) or (not next_dt):
        return None

    if (now.date() != next_dt.date()) and not config.all:
        return None

    debug(config, f"begin: {next_dt.date()}")
    debug(config, f"next_event: {next_event}")

    # If meeteing is soon to begin or we have chosen to include
    # meetings for the next days+, show time in "human format", e.g. `in 5 minutes`
    if (now + timedelta(seconds=config.humanize_after_sec) > next_dt) or (
        now.date() != next_dt.date()
    ):
        begin_str = humanize(next_dt.timestamp() - now.timestamp())
    else:
        begin_str = f"@{next_dt.strftime('%H:%M')}"

    return Event(
        name=next_event.get("SUMMARY", "Unknown").strip(),
        begin=begin_str,
        alert=now + timedelta(seconds=config.alert_sec_before) > next_dt,
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


def executor() -> None:
    """
    Output for Executor (Gnome Panel)
    """

    event = upcoming_event()

    if not event:
        return

    print(f"{event.name} {event.begin}{'<executor.css.red>' if event.alert else ''}")

    try:
        sys.stdout.flush()
    except BrokenPipeError:
        pass


if __name__ == "__main__":
    status()
