from icalstatus.date import humanize


def test_humanize() -> None:
    assert humanize(4600) == "in 1 hour"
    assert humanize(3600) == "in 1 hour"
    assert humanize(1800) == "in 30 minutes"
    assert humanize(200) == "in 3 minutes"
    assert humanize(45) == "in 45 seconds"
    assert humanize(-4600) == "1 hour ago"
    assert humanize(-3600) == "1 hour ago"
    assert humanize(-1800) == "30 minutes ago"
    assert humanize(-200) == "3 minutes ago"
    assert humanize(-45) == "45 seconds ago"
