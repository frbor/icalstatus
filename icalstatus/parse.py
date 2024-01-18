#!/usr/bin/env python3

import caep
import icalendar  # type: ignore
import pytz
from pydantic import BaseModel, Field

from icalstatus.date import get_event_dt


class Config(BaseModel):
    timezone: str = Field("CET", description="Timezone")
    file: str = Field(description="File to parse")


def parse(config: Config, data: str) -> None:
    tzinfo = pytz.timezone(config.timezone)

    cal = icalendar.Calendar.from_ical(data)
    for e in cal.walk():
        if not e.name == "VEVENT":
            continue
        begin = get_event_dt(e, tzinfo)
        end = get_event_dt(e, tzinfo, "DTEND")
        print(
            f"""
{e.get('SUMMARY', 'Unknown')}

Organizer: {e.get('ORGANIZER', 'Unknown')}
Location: {e.get('LOCATION', 'Unknown')}

Start: {begin}
End:   {end}

{e.get('DESCRIPTION', 'Unknown')}"""
        )


def main() -> None:
    config: Config = caep.load(Config, "ICAL parse", "icalstatus", "config", "parse")

    data = open(config.file).read()
    parse(config, data)


if __name__ == "__main__":
    main()
