#!/usr/bin/env python3


import caep
import ics
from pydantic import BaseModel, Field


class Config(BaseModel):

    timezone: str = Field("Europe/Oslo", description="Timezone")
    file: str = Field(description="File to parse")


def parse(config: Config, data: str) -> None:
    for e in ics.Calendar(data).events:
        e.begin = e.begin.replace(tzinfo=config.timezone)
        e.end = e.end.replace(tzinfo=config.timezone)
        name = e.name if e.name else "Unknown"
        organizer = e.organizer if e.organizer else "Unknown"
        location = e.location if e.location else "Unknown"
        description = e.description if e.description else "No description"
        print(
            f"""
{name}

Organizer: {organizer}
Location: {location}

Start: {e.begin}
End:   {e.end}

{description}"""
        )


def main() -> None:

    config: Config = caep.load(Config, "ICAL parse", "icalstatus", "config", "parse")

    data = open(config.file).read()
    parse(config, data)


if __name__ == "__main__":
    main()
