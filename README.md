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

All options can be specified in the same configuration file and
the other available options are:

```
usage: ICAL Status [-h] [--calendar-url CALENDAR_URL] [--timezone TIMEZONE] [--no-verify] [--proxy PROXY] [--all] [--humanize-after HUMANIZE_AFTER]
                   [--alert-sec-before ALERT_SEC_BEFORE]

options:
  -h, --help            show this help message and exit
  --calendar-url CALENDAR_URL
                        URI for ICS Calendar
  --timezone TIMEZONE   Timezone (default=CET)
  --no-verify           Ignore SSL verification errors
  --proxy PROXY         Proxy for ICS url
  --all                 Include events that are not today
  --humanize-after-sec HUMANIZE_AFTER
                        Humanize meeting date if less than this many seconds 
                        until meeting
  --alert-sec-before ALERT_SEC_BEFORE
                        Alert meeting at specified seconds before start. 
                        This will switch class for output on waybar.
```

Options:

### `all`

By default, only todays events will be shown (and output will be empty if
no more event the same day). Specify `--all` to show all events.

### `humanize-after-sec`

Meeting time will be show in "human format" if it less than this
many seconds until the meeting. E.g. if the time is 11:30 and you
have specified `--humanize-after-sec 3600` the output will be

```
<Meeting> in 30 minutes
```

If you at 11:30 specified `--humaize-after` it will show

```
<Meeting> @12:00
```

### `alert-sec-before`

This option is only relevant for `icalwaybar`. If is is less than this
many seconds to the meeting, it will use `class: alert`, otherwize
`class: normal`. Examples (when running the command at 11:50):

```
icalwaybar --alert-sec-before 900
{"text": "<Meeting> in 10 minutes", "class": "alert"}
```

```
icalwaybar --alert-sec-before 300
{"text": "<Meeting> in 10 minutes", "class": "normal"}
```

# Parse

A tool to parse ics files and output summary to stdout is included:

- `icalparse`

# Credits

Original code/idea from Geir Skjøtskift (https://github.com/geirskjo).
