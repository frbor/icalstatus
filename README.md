# ICAL Status - Status bar for ICS Calenders

# Installation

```bash
pip install icalstatus
```

# Status

To run, one of:

- `icalstatus`
- `icalwaybar`

## Configuration

For the status you must specify you calendar URL either on the commandline or in the 
configuration file `~/.config/icalstatus/config`:

E.g, for OWA:

```
[DEFAULT]
calendar-url=https://(HOST)/owa/calendar/(...)/calendar.ics
```

Other options:

```
usage: ICAL Status [-h] [--calendar-url CALENDAR_URL] [--timezone TIMEZONE] [--no-verify] [--proxy PROXY] [--all] [--humanize-after HUMANIZE_AFTER]
                   [--alert-sec-before ALERT_SEC_BEFORE]

options:
  -h, --help            show this help message and exit
  --calendar-url CALENDAR_URL
                        URI for ICS Calendar
  --timezone TIMEZONE   Timezone
  --no-verify           Ignore SSL verification errors
  --proxy PROXY         Proxy for ICS url
  --all                 Include events that are not today
  --humanize-after HUMANIZE_AFTER
                        Humanize meeting date if less than this many seconds until meeting
  --alert-sec-before ALERT_SEC_BEFORE
                        Alert meeting at specified seconds before start. This will switch class for output on waybar.
```

# Parse

A tool to parse ics files and output summary to stdout is included:

- `icalparse`

# Credits

Original code/idea from Geir Skjøtskift (https://github.com/bunzen).
