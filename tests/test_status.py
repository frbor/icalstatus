import json
from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

import icalstatus.status as status_module
from icalstatus.calendar import CalendarEntry
from icalstatus.status import Config, Event, status_event

NOW = datetime(2026, 8, 4, 9, tzinfo=ZoneInfo("UTC"))
START = datetime(2026, 8, 4, 9, 4, tzinfo=ZoneInfo("UTC"))


@pytest.mark.parametrize(
    ("title", "location", "limits", "expected"),
    [
        ("Standup", "Oslo", {}, "Standup [Oslo]"),
        ("T" * 40, "R" * 30, {}, "T" * 40 + " [" + "R" * 30 + "]"),
        ("T" * 41, "R" * 31, {}, "T" * 39 + "… [" + "R" * 29 + "…]"),
        (
            "Planning",
            "Oslo room",
            {"max_title_length": 5, "max_location_length": 4},
            "Plan… [Osl…]",
        ),
        (
            "Planning",
            "Oslo room",
            {"max_title_length": 0, "max_location_length": 4},
            "Planning [Osl…]",
        ),
        (
            "Planning",
            "Oslo room",
            {"max_title_length": 5, "max_location_length": 0},
            "Plan… [Oslo room]",
        ),
        (
            "T" * 41,
            "R" * 31,
            {"max_title_length": 0, "max_location_length": 0},
            "T" * 41 + " [" + "R" * 31 + "]",
        ),
        ("T" * 41, None, {}, "T" * 39 + "…"),
        (
            "Møte",
            "Øst",
            {"max_title_length": 1, "max_location_length": 1},
            "… […]",
        ),
    ],
)
def test_status_event_limits_title_and_location_independently(
    title: str, location: str | None, limits: dict[str, int], expected: str
) -> None:
    config = Config.model_validate(
        {"calendar_url": "https://example.com/calendar.ics", **limits}
    )
    entry = CalendarEntry(title, START, location)

    assert status_event(config, entry, NOW) == Event(
        name=expected, begin="in 4 minutes", alert=True
    )


@pytest.mark.parametrize(
    ("render", "expected"),
    [
        (status_module.status, "Mø<&… [Ø&…] in 4 minutes"),
        (status_module.waybar, "Mø&lt;&amp;… [Ø&amp;…] in 4 minutes"),
        (
            status_module.executor,
            "Mø<&… [Ø&…] in 4 minutes<executor.css.red>",
        ),
    ],
)
def test_outputs_preserve_time_and_formatting_with_truncated_names(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    render: Callable[[], None],
    expected: str,
) -> None:
    config = Config.model_validate(
        {
            "calendar_url": "https://example.com/calendar.ics",
            "max_title_length": 5,
            "max_location_length": 3,
        }
    )
    event = status_event(config, CalendarEntry("Mø<&te", START, "Ø&st"), NOW)
    monkeypatch.setattr(status_module, "upcoming_event", lambda: event)

    render()

    output = capsys.readouterr().out.strip()
    if render is status_module.waybar:
        assert json.loads(output) == {"text": expected, "class": "alert"}
    else:
        assert output == expected
