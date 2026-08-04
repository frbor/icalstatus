import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Never, cast
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from icalstatus import ews
from icalstatus.calendar import CalendarEntry
from icalstatus.ews import EwsCalendarSource, PasswordLookupError, password_from_gopass
from icalstatus.ics import IcsCalendarSource
from icalstatus.status import Config, Event, next_calendar_entry, status_event

UTC = ZoneInfo("UTC")


class RecordingSource:
    def __init__(self, entries: tuple[CalendarEntry, ...]) -> None:
        self._entries = entries
        self.window: tuple[datetime, datetime] | None = None

    def entries(self, start: datetime, end: datetime) -> tuple[CalendarEntry, ...]:
        self.window = (start, end)
        return self._entries


def test_next_calendar_entry_is_source_independent() -> None:
    now = datetime(2026, 8, 4, 9, tzinfo=UTC)
    earlier = CalendarEntry("Earlier", datetime(2026, 8, 4, 8, tzinfo=UTC))
    later = CalendarEntry("Later", datetime(2026, 8, 4, 11, tzinfo=UTC))
    next_entry = CalendarEntry("Next", datetime(2026, 8, 4, 10, tzinfo=UTC))
    source = RecordingSource((later, earlier, next_entry))

    assert next_calendar_entry(source, now) == next_entry
    assert source.window == (now, datetime(2026, 8, 11, 9, tzinfo=UTC))


def test_calendar_entry_has_source_independent_status_rendering() -> None:
    now = datetime(2026, 8, 4, 9, tzinfo=UTC)
    entry = CalendarEntry("Standup", datetime(2026, 8, 4, 9, 4, tzinfo=UTC))

    assert status_event(
        Config.model_validate({"calendar_url": "https://example.com/calendar.ics"}),
        entry,
        now,
    ) == Event(name="Standup", begin="in 4 minutes", alert=True)


@pytest.mark.parametrize(
    "values",
    [
        {},
        {"exchange_server": "mail.example.com"},
        {
            "exchange_server": "mail.example.com",
            "exchange_user": r"DOMAIN\fredrikb",
            "exchange_mailbox": "fredrikb@example.com",
        },
        {
            "exchange_server": "mail.example.com",
            "exchange_user": r"DOMAIN\fredrikb",
            "exchange_password_path": "work/exchange",
        },
        {
            "calendar_url": "https://example.com/calendar.ics",
            "exchange_server": "mail.example.com",
            "exchange_user": r"DOMAIN\fredrikb",
            "exchange_mailbox": "fredrikb@example.com",
            "exchange_password_path": "work/exchange",
        },
    ],
)
def test_config_rejects_invalid_source_combinations(values: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        Config.model_validate(values)


def test_config_accepts_each_complete_source() -> None:
    assert Config.model_validate(
        {"calendar_url": "https://example.com/calendar.ics"}
    ).calendar_url
    config = Config.model_validate(
        {
            "exchange_server": "mail.example.com",
            "exchange_user": r"DOMAIN\fredrikb",
            "exchange_mailbox": "fredrikb@example.com",
            "exchange_password_path": "work/exchange",
        }
    )
    assert config.exchange_server == "mail.example.com"


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text
        self.status_checked = False

    def raise_for_status(self) -> None:
        self.status_checked = True


def test_ics_source_expands_recurrences(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calendar_data = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:daily@example.com
DTSTART:20260804T100000Z
DTEND:20260804T103000Z
RRULE:FREQ=DAILY;COUNT=2
SUMMARY:Daily meeting
END:VEVENT
END:VCALENDAR
"""
    response = FakeResponse(calendar_data)
    request: dict[str, object] = {}

    def fake_get(url: str, **kwargs: object) -> FakeResponse:
        request["url"] = url
        request.update(kwargs)
        return response

    monkeypatch.setattr("icalstatus.ics.requests.get", fake_get)
    source = IcsCalendarSource(
        url="https://example.com/calendar.ics",
        timezone=UTC,
        no_verify=True,
        proxy="http://proxy.example.com",
    )

    entries = source.entries(
        datetime(2026, 8, 4, 9, tzinfo=UTC),
        datetime(2026, 8, 6, 9, tzinfo=UTC),
    )

    assert [entry.summary for entry in entries] == ["Daily meeting", "Daily meeting"]
    assert [entry.start.hour for entry in entries] == [10, 10]
    assert request == {
        "url": "https://example.com/calendar.ics",
        "timeout": 10,
        "verify": False,
        "proxies": {
            "http": "http://proxy.example.com",
            "https": "http://proxy.example.com",
        },
    }
    assert response.status_checked


def test_password_from_gopass_uses_secret_path_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invocation: dict[str, object] = {}

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        invocation["args"] = args
        invocation.update(kwargs)
        return subprocess.CompletedProcess(args, 0, "correct horse\n", "")

    monkeypatch.setattr("icalstatus.ews.subprocess.run", fake_run)

    assert password_from_gopass("work/exchange/user") == "correct horse"
    assert invocation["args"] == [
        "gopass",
        "show",
        "--password",
        "work/exchange/user",
    ]
    assert invocation["stderr"] == subprocess.DEVNULL


def test_password_from_gopass_rejects_empty_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 0, "\n", "")

    monkeypatch.setattr("icalstatus.ews.subprocess.run", fake_run)

    with pytest.raises(PasswordLookupError, match="empty password"):
        password_from_gopass("work/exchange/user")


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (FileNotFoundError(), "gopass executable was not found"),
        (
            subprocess.CalledProcessError(1, ["gopass"], stderr="LEAKED_PASSWORD"),
            "gopass could not read the configured secret",
        ),
    ],
)
def test_password_from_gopass_reports_safe_errors(
    monkeypatch: pytest.MonkeyPatch, error: Exception, message: str
) -> None:
    def fake_run(*args: object, **kwargs: object) -> Never:
        raise error

    monkeypatch.setattr("icalstatus.ews.subprocess.run", fake_run)

    with pytest.raises(PasswordLookupError, match=message) as raised:
        password_from_gopass("work/exchange/user")
    assert "LEAKED_PASSWORD" not in str(raised.value)


@dataclass
class FakeEwsItem:
    subject: str | None
    start: datetime


class FakeEwsItems:
    def __init__(self, items: list[FakeEwsItem]) -> None:
        self.items = items
        self.fields: tuple[str, ...] | None = None

    def only(self, *fields: str) -> list[FakeEwsItem]:
        self.fields = fields
        return self.items


class FakeCalendar:
    def __init__(self, items: FakeEwsItems) -> None:
        self.items = items
        self.window: tuple[datetime, datetime] | None = None

    def view(self, *, start: datetime, end: datetime) -> FakeEwsItems:
        self.window = (start, end)
        return self.items


@dataclass
class FakeAccount:
    calendar: FakeCalendar


def test_ews_source_returns_normalized_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    start = datetime(2026, 8, 4, 9, tzinfo=UTC)
    end = datetime(2026, 8, 11, 9, tzinfo=UTC)
    items = FakeEwsItems(
        [
            FakeEwsItem(None, datetime(2026, 8, 4, 11, tzinfo=UTC)),
            FakeEwsItem(" Standup ", datetime(2026, 8, 4, 10, tzinfo=UTC)),
        ]
    )
    calendar = FakeCalendar(items)
    account = FakeAccount(calendar)
    calls: dict[str, object] = {}

    def fake_credentials(*, username: str, password: str) -> object:
        calls["credentials"] = (username, password)
        return object()

    def fake_configuration(*, server: str, credentials: object) -> object:
        configuration = object()
        calls["configuration"] = (server, credentials, configuration)
        return configuration

    def fake_account(**kwargs: object) -> FakeAccount:
        calls["account"] = kwargs
        return account

    monkeypatch.setattr(ews, "password_from_gopass", lambda path: "resolved-password")
    monkeypatch.setattr(ews, "Credentials", fake_credentials)
    monkeypatch.setattr(ews, "Configuration", fake_configuration)
    monkeypatch.setattr(ews, "Account", fake_account)
    protocol = vars(ews)["BaseProtocol"]
    monkeypatch.setattr(protocol, "HTTP_ADAPTER_CLS", object)

    source = EwsCalendarSource(
        server="mail.example.com",
        user=r"DOMAIN\fredrikb",
        mailbox="fredrikb@example.com",
        password_path="work/exchange/user",
        timezone=UTC,
        no_verify=True,
    )
    entries = source.entries(start, end)

    assert entries == (
        CalendarEntry("Standup", datetime(2026, 8, 4, 10, tzinfo=UTC)),
        CalendarEntry("Unknown", datetime(2026, 8, 4, 11, tzinfo=UTC)),
    )
    assert calls["credentials"] == (r"DOMAIN\fredrikb", "resolved-password")
    configuration_call = cast(tuple[str, object, object], calls["configuration"])
    account_call = cast(dict[str, object], calls["account"])
    assert configuration_call[0] == "mail.example.com"
    assert account_call == {
        "primary_smtp_address": "fredrikb@example.com",
        "config": configuration_call[2],
        "autodiscover": False,
        "access_type": vars(ews)["DELEGATE"],
    }
    assert calendar.window == (start, end)
    assert items.fields == ("subject", "start")
    assert protocol.HTTP_ADAPTER_CLS is vars(ews)["NoVerifyHTTPAdapter"]
