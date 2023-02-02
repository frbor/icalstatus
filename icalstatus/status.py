#!/usr/bin/env python3
"""Statusbar ics calendar"""

import html
import json
import sys
from dataclasses import dataclass
from typing import Optional

import arrow
import caep
import ics
import requests
from dateutil import rrule  # type: ignore
from pydantic import BaseModel, Field
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

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


def is_recurring(event: ics.Event) -> bool:
    """Check if it is a recurring event"""

    return any(filter(lambda x: x.name == "RRULE", event.extra))  # type: ignore


def get_rrule(event: ics.Event) -> tuple[str, bool]:
    """Extract the rrule text from an event"""

    for extra in event.extra:
        if extra.name == "RRULE":
            return extra.value, True

    return "", False


def get_next_datetime(event: ics.Event, now: arrow) -> arrow.Arrow:
    """Check if it is a recurring event, and if so get next event time"""

    if is_recurring(event):

        ruletext, ok = get_rrule(event)
        if not ok:
            return event.begin
        rule = rrule.rrulestr(ruletext, dtstart=event.begin.datetime)
        nextrule = rule.after(now.datetime)
        if not nextrule:
            return event.begin
        return arrow.get(nextrule)

    return event.begin


def ics_next_event(ics_data: str, now: arrow, timezone: str) -> Optional[ics.Event]:
    curr = None
    diff = None

    cal = ics.Calendar(ics_data)

    event = None
    for event in cal.events:
        # Set correct timezone
        event.begin = event.begin.replace(tzinfo=timezone)
        if event.begin.datetime < now:
            if is_recurring(event):
                nextrule = get_next_datetime(event, now)
                if nextrule < now:
                    continue
                thisdiff = nextrule - now
                if not curr or thisdiff < diff:
                    diff = thisdiff
                    curr = event
            continue
        thisdiff = event.begin.datetime - now
        if not curr or thisdiff < diff:
            diff = thisdiff
            curr = event

    return curr


def upcoming_event() -> Optional[Event]:
    """Get the next event closest in time"""

    config: Config = caep.load(Config, "ICAL Status", "icalstatus", "config", "status")

    now = arrow.now().replace(tzinfo=config.timezone)
    next = ics_next_event(
        get_data(config.calendar_url, config.no_verify, config.proxy),
        now,
        config.timezone,
    )

    if not next:
        return None

    begin = get_next_datetime(next, now).replace(tzinfo=config.timezone)

    if (now.date() != begin.date()) and not config.all:
        return None

    # If meeteing is soon to begin or we have chosen to include
    # meetings for the next days+, show time in "human format", e.g. `in 5 minutes`
    if (now.shift(seconds=config.humanize_after_sec) > begin) or (
        now.date() != begin.date()
    ):
        begin_str = begin.humanize()
    else:
        begin_str = f"@{begin.format('HH:mm')}"

    return Event(
        name=next.name.strip(),
        begin=begin_str,
        alert=now.shift(seconds=config.alert_sec_before) > begin,
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
