from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import icalendar  # type: ignore[import-untyped]
import recurring_ical_events  # type: ignore[import-untyped]
import requests
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

from .calendar import CalendarEntry
from .date import get_event_dt

disable_warnings(InsecureRequestWarning)


class CalendarParseError(Exception):
    """Raised when downloaded iCalendar data cannot be parsed."""


@dataclass(frozen=True, slots=True)
class IcsCalendarSource:
    url: str
    timezone: ZoneInfo
    no_verify: bool = False
    proxy: str | None = None

    def entries(self, start: datetime, end: datetime) -> tuple[CalendarEntry, ...]:
        proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None
        response = requests.get(
            self.url,
            timeout=10,
            verify=not self.no_verify,
            proxies=proxies,
        )
        response.raise_for_status()

        try:
            calendar = icalendar.Calendar.from_ical(response.text)
        except ValueError as error:
            raise CalendarParseError(error) from error

        entries = (
            CalendarEntry(
                summary=str(event.get("SUMMARY", "Unknown")).strip() or "Unknown",
                start=get_event_dt(event, self.timezone),
            )
            for event in recurring_ical_events.of(calendar).between(start, end)
        )
        return tuple(sorted(entries, key=lambda entry: entry.start))
