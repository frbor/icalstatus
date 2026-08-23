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
from requests.adapters import HTTPAdapter

from .calendar import CalendarEntry


class PasswordLookupError(RuntimeError):
    """Raised when an Exchange password cannot be retrieved from gopass."""


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
            location = cast(str | None, item.location)
            if location is not None and self.location_strip_regex is not None:
                location = re.sub(self.location_strip_regex, "", location)
            entries.append(
                CalendarEntry(
                    summary=subject.strip()
                    if subject and subject.strip()
                    else "Unknown",
                    start=item_start.astimezone(self.timezone),
                    location=location.strip()
                    if location and location.strip()
                    else None,
                )
            )
        return tuple(sorted(entries, key=lambda entry: entry.start))
