from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class CalendarEntry:
    """A calendar entry normalized for source-independent processing."""

    summary: str
    start: datetime


class CalendarSource(Protocol):
    """A source capable of returning entries in a requested time window."""

    def entries(self, start: datetime, end: datetime) -> Sequence[CalendarEntry]: ...
