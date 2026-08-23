#!/usr/bin/env python3
"""Statusbar ics calendar"""

import html
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Self
from zoneinfo import ZoneInfo

import caep
from pydantic import BaseModel, Field, field_validator, model_validator

from .calendar import CalendarEntry, CalendarSource
from .date import humanize
from .ews import EwsCalendarSource
from .ics import IcsCalendarSource


@dataclass
class Event:
    name: str
    begin: str
    alert: bool


class Config(BaseModel):
    calendar_url: str | None = Field(default=None, description="URI for ICS Calendar")
    exchange_server: str | None = Field(
        default=None, description="Exchange server hostname"
    )
    exchange_user: str | None = Field(
        default=None, description="Exchange authentication username"
    )
    exchange_mailbox: str | None = Field(
        default=None, description="Primary SMTP address of the Exchange mailbox"
    )
    exchange_password_path: str | None = Field(
        default=None, description="gopass path containing the Exchange password"
    )
    location_strip_regex: str | None = Field(
        default=None,
        description="Regex used to remove parts of Exchange meeting locations",
    )
    timezone: str = Field(default="CET", description="Timezone (default=CET)")
    no_verify: bool = Field(default=False, description="Ignore SSL verification errors")
    proxy: str | None = Field(default=None, description="Proxy for ICS url")

    all: bool = Field(default=False, description="Include events that are not today")
    debug: bool = Field(default=False, description="Add debug output")

    humanize_after_sec: int = Field(
        default=3600,
        description="Humanize meeting date if less than "
        "this many seconds until meeting",
    )

    alert_sec_before: int = Field(
        default=300,
        description="Alert meeting at specified seconds before start. "
        "This will switch class for output on waybar.",
    )

    @field_validator("location_strip_regex")
    @classmethod
    def validate_location_strip_regex(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                re.compile(value)
            except re.error as error:
                raise ValueError(
                    "location-strip-regex must be a valid regex"
                ) from error
        return value

    @model_validator(mode="after")
    def validate_calendar_source(self) -> Self:
        exchange_values = (
            self.exchange_server,
            self.exchange_user,
            self.exchange_mailbox,
            self.exchange_password_path,
        )
        has_exchange_value = any(value is not None for value in exchange_values)
        has_complete_exchange = all(
            value is not None and bool(value.strip()) for value in exchange_values
        )

        if self.calendar_url is not None:
            if not self.calendar_url.strip():
                raise ValueError("calendar-url cannot be empty")
            if has_exchange_value:
                raise ValueError(
                    "calendar-url and Exchange settings cannot be used together"
                )
        elif not has_complete_exchange:
            raise ValueError(
                "set calendar-url or all of exchange-server, exchange-user, "
                "exchange-mailbox, and exchange-password-path"
            )
        return self


def remove_non_printable(value: str) -> str:
    return "".join(i for i in value if i.isprintable())


def debug(config: Config, message: str) -> None:
    if not config.debug:
        return

    print(f"DEBUG: {message}")


def calendar_source(config: Config, timezone: ZoneInfo) -> CalendarSource:
    if config.calendar_url is not None:
        return IcsCalendarSource(
            url=config.calendar_url,
            timezone=timezone,
            no_verify=config.no_verify,
            proxy=config.proxy,
        )

    if (
        config.exchange_server is None
        or config.exchange_user is None
        or config.exchange_mailbox is None
        or config.exchange_password_path is None
    ):
        raise ValueError("incomplete Exchange configuration")
    return EwsCalendarSource(
        server=config.exchange_server,
        user=config.exchange_user,
        mailbox=config.exchange_mailbox,
        password_path=config.exchange_password_path,
        timezone=timezone,
        no_verify=config.no_verify,
        location_strip_regex=config.location_strip_regex,
    )


def next_calendar_entry(source: CalendarSource, now: datetime) -> CalendarEntry | None:
    entries = source.entries(now, now + timedelta(days=7))
    return min(
        (entry for entry in entries if entry.start >= now),
        key=lambda entry: entry.start,
        default=None,
    )


def status_event(config: Config, entry: CalendarEntry, now: datetime) -> Event | None:
    if now.date() != entry.start.date() and not config.all:
        return None

    debug(config, f"begin: {entry.start.date()}")
    debug(config, f"next_event: {entry}")

    # If the meeting is soon to begin or meetings on future days are included,
    # show the time in human format, e.g. `in 5 minutes`.
    if (now + timedelta(seconds=config.humanize_after_sec) > entry.start) or (
        now.date() != entry.start.date()
    ):
        begin = humanize(entry.start.timestamp() - now.timestamp())
    else:
        begin = f"@{entry.start.strftime('%H:%M')}"

    name = entry.summary
    if entry.location is not None:
        name = f"{name} [{entry.location}]"

    return Event(
        name=name,
        begin=begin,
        alert=now + timedelta(seconds=config.alert_sec_before) > entry.start,
    )


def upcoming_event() -> Event | None:
    """Get the next event closest in time"""

    config: Config = caep.load(Config, "ICAL Status", "icalstatus", "config", "status")

    tzinfo = ZoneInfo(config.timezone)
    now = datetime.now().astimezone(tzinfo)

    next_entry = next_calendar_entry(calendar_source(config, tzinfo), now)
    if next_entry is None:
        return None
    return status_event(config, next_entry, now)


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
