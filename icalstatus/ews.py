import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import cast
from zoneinfo import ZoneInfo

from exchangelib import (  # type: ignore[import-untyped]
    DELEGATE,
    Account,
    Configuration,
    Credentials,
)
from exchangelib.protocol import (  # type: ignore[import-untyped]
    BaseProtocol,
    NoVerifyHTTPAdapter,
)
from exchangelib.winzone import MS_TIMEZONE_TO_IANA_MAP  # type: ignore[import-untyped]
from requests.adapters import HTTPAdapter

from .calendar import CalendarEntry


class PasswordLookupError(RuntimeError):
    """Raised when an Exchange password cannot be retrieved from gopass."""


def _configure_empty_timezone_fallback(timezone: ZoneInfo) -> None:
    """Use the configured timezone when Exchange returns an empty timezone ID."""

    MS_TIMEZONE_TO_IANA_MAP[""] = timezone.key


def _normalize_location(location: str | None, strip_regex: str | None) -> str | None:
    if location is None:
        return None
    if strip_regex is not None:
        location = re.sub(strip_regex, "", location)
    location = re.sub(r"^[;\s]+|[;\s]+$", "", location)
    return location or None


def password_from_gopass(secret_path: str) -> str:
    """Return only the password stored at a gopass secret path."""

    try:
        result = subprocess.run(
            ["gopass", "show", "--password", secret_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except FileNotFoundError as error:
        raise PasswordLookupError("gopass executable was not found") from error
    except subprocess.CalledProcessError as error:
        raise PasswordLookupError(
            "gopass could not read the configured secret"
        ) from error

    password = result.stdout.rstrip("\r\n")
    if not password:
        raise PasswordLookupError("gopass returned an empty password")
    return password


@dataclass(frozen=True, slots=True)
class EwsCalendarSource:
    server: str
    user: str
    mailbox: str
    password_path: str
    timezone: ZoneInfo
    no_verify: bool = False
    location_strip_regex: str | None = None

    def entries(self, start: datetime, end: datetime) -> tuple[CalendarEntry, ...]:
        password = password_from_gopass(self.password_path)
        credentials = Credentials(username=self.user, password=password)
        _configure_empty_timezone_fallback(self.timezone)

        BaseProtocol.HTTP_ADAPTER_CLS = (
            NoVerifyHTTPAdapter if self.no_verify else HTTPAdapter
        )
        configuration = Configuration(server=self.server, credentials=credentials)
        account = Account(
            primary_smtp_address=self.mailbox,
            config=configuration,
            autodiscover=False,
            access_type=DELEGATE,
        )

        items = account.calendar.view(start=start, end=end).only(
            "subject", "start", "location"
        )
        entries: list[CalendarEntry] = []
        for item in items:
            item_start = cast(datetime, item.start)
            if item_start.tzinfo is None:
                raise ValueError("EWS returned a calendar entry without a timezone")
            subject = cast(str | None, item.subject)
            location = _normalize_location(
                cast(str | None, item.location), self.location_strip_regex
            )
            entries.append(
                CalendarEntry(
                    summary=subject.strip()
                    if subject and subject.strip()
                    else "Unknown",
                    start=item_start.astimezone(self.timezone),
                    location=location,
                )
            )
        return tuple(sorted(entries, key=lambda entry: entry.start))
