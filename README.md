# ICAL Status - Status bar for ICS Calenders

# Changelog

## 0.1.0
- Require python 3.12+
- Upgrade dependencies
- Fix bug in timezone handling

## 0.0.6
- Require python 3.11+ and upgrade dependencies

# Installation

```bash
pip install icalstatus
```

# Status

To run, one of:

- `icalstatus`
- `icalwaybar`
- `icalexecutor`

## Configuration

For the status you must configure exactly one calendar source, either on the command
line or in the configuration file `~/.config/icalstatus/config`.

For an ICS URL:

E.g, for OWA:

```
[DEFAULT]
calendar-url=https://(HOST)/owa/calendar/(...)/calendar.ics
```

For an on-premises Exchange server using EWS:

```ini
[DEFAULT]
exchange-server=mail.example.com
exchange-user=DOMAIN\user
exchange-mailbox=user@example.com
exchange-password-path=work/exchange/user
location-strip-regex=^OSL\s*|\s*\(\d+\)$
```

`exchange-server` is a hostname. `exchange-user` is the authentication username and
may use the `DOMAIN\username` form expected by an on-premises server.
`exchange-mailbox` is the mailbox's primary SMTP address. Authentication is detected
by `exchangelib`. Calendar entries are fetched for the next seven days.
When Exchange provides a calendar location, it is shown after the meeting subject in
the form `Subject [Room]`. The OWA/ICS source behavior is unchanged.
Use `location-strip-regex` to remove Exchange-specific prefixes or suffixes before
the location is displayed. For example, `OSL Angler-802A (4)` becomes
`Angler-802A` with the example above.

The Exchange password is not stored in the configuration. Store it in
[`gopass`](https://www.gopass.pw/) and configure only its secret path. The equivalent
lookup performed by `icalstatus` is:

```bash
gopass show --password work/exchange/user
```

The `gopass` executable and an initialized, unlockable password store must be
available in the environment where `icalstatus` runs.

All options can be specified in the same configuration file and
the other available options are:

```
usage: ICAL Status [-h] [--calendar-url CALENDAR_URL] [--timezone TIMEZONE] [--no-verify] [--proxy PROXY] [--all] [--humanize-after HUMANIZE_AFTER]
                   [--alert-sec-before ALERT_SEC_BEFORE]

options:
  -h, --help            show this help message and exit
  --calendar-url CALENDAR_URL
                        URI for ICS Calendar
  --exchange-server EXCHANGE_SERVER
                        Exchange server hostname
  --exchange-user EXCHANGE_USER
                        Exchange authentication username
  --exchange-mailbox EXCHANGE_MAILBOX
                        Primary SMTP address of the Exchange mailbox
  --exchange-password-path EXCHANGE_PASSWORD_PATH
                        gopass path containing the Exchange password
  --location-strip-regex LOCATION_STRIP_REGEX
                        Regex used to remove parts of Exchange meeting locations
  --max-title-length MAX_TITLE_LENGTH
                        Maximum meeting title characters, including ellipsis (0 disables)
  --max-location-length MAX_LOCATION_LENGTH
                        Maximum location characters, including ellipsis (0 disables)
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

### `max-title-length` and `max-location-length`

Meeting titles are limited to **40 characters** and rooms/locations to
**30 characters** by default in `icalstatus`, `icalwaybar`, and `icalexecutor`.
Each value is shortened independently with a trailing `…`, which counts toward
its limit. The location brackets and meeting time are outside these limits.
Lengths count Unicode characters before Waybar HTML escaping.

Set either option to `0` to disable its limit. Negative values are rejected.
For example:

```bash
icalwaybar --max-title-length 50 --max-location-length 20
icalstatus --max-title-length 0 --max-location-length 0
```

The same settings can be added to `~/.config/icalstatus/config` alongside your
calendar source:

```ini
[DEFAULT]
max-title-length=50
max-location-length=20
```

These settings do not affect `icalparse`.

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

If you at 11:30 specified `--humanize-after` it will show

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

### Output specific formatting

#### `icalexecutor`

If the meeting is within `--alert-sec-before`, `<executor.css.red>` will be added to the output.

This means that you can specify the CSS class `red` according to [https://raujonas.github.io/executor/docs/configuration/custom-css/](https://raujonas.github.io/executor/docs/configuration/custom-css/):

```
.red {
    color: red;
}
```

.e.g in `~/.config/executor@raujonas.github.io/custom.css`.

# Parse

A tool to parse ics files and output summary to stdout is included:

- `icalparse`

# Credits

Original code/idea from Geir Skjøtskift (https://github.com/geirskjo).
