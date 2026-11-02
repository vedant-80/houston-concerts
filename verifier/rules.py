"""The task's rules, written again from the README for the verifier alone: it imports none of the
plugin's code, so a bug in a tool cannot hide itself by agreeing with its own checker. (A verifier
may not import datetime, so calendar dates are checked with plain arithmetic.)"""

import re

TOP = 20
DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
TIME = re.compile(r"(\d{2}:\d{2})?")
DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def is_date(text):
    """Whether ``text`` is a real calendar date written YYYY-MM-DD."""
    match = DATE.fullmatch(text) if isinstance(text, str) else None
    if not match:
        return False
    year, month, day = (int(part) for part in match.groups())
    if not 1 <= month <= 12:
        return False
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    return 1 <= day <= DAYS[month - 1] + (1 if month == 2 and leap else 0)


def range_problem(start, end):
    for name, text in (("start_date", start), ("end_date", end)):
        if not is_date(text):
            return f"{name} {text!r} is not a calendar date YYYY-MM-DD"
    if start > end:
        return f"start_date {start} is after end_date {end}"
    return None


def show_problem(show, start, end):
    """What is malformed about a pinned show, or None."""
    if not show.artist.strip():
        return f"show {show.event_id} has no artist"
    if not is_date(show.date) or not start <= show.date <= end:
        return f"show {show.event_id} is dated {show.date!r}, outside the window {start} to {end}"
    if not TIME.fullmatch(show.time):
        return f"show {show.event_id} has time {show.time!r}, not HH:MM or empty"
    return None


def show_order(show):
    return (show.date, show.time or "99:99", show.event_id)


def expected_rows(pin, first, last):
    """Every artist headlining a show from ``first`` to ``last`` and their first such show, most listeners
    first, ties by artist name: as plain dicts."""
    listeners = {entry.artist: entry.listeners for entry in pin.listeners}
    earliest = {}
    for show in pin.shows:
        if not first <= show.date <= last:
            continue
        best = earliest.get(show.artist)
        if best is None or show_order(show) < show_order(best):
            earliest[show.artist] = show
    rows = [{"artist": a, "listeners": listeners[a], "date": s.date, "venue": s.venue} for a, s in earliest.items()]
    return sorted(rows, key=lambda row: (-row["listeners"], row["artist"]))


def plain(row):
    return {"artist": row.artist, "listeners": row.listeners, "date": row.date, "venue": row.venue}


def rows_problem(rows):
    """What is malformed in a list of ConcertRow, or None."""
    seen = set()
    for position, row in enumerate(rows, 1):
        where = f"row #{position} ({row.artist})"
        if not row.artist.strip():
            return f"row #{position} has no artist"
        if row.listeners < 0:
            return f"{where} has {row.listeners} listeners, below 0"
        if not is_date(row.date):
            return f"{where} has date {row.date!r}, not a calendar date YYYY-MM-DD"
        if row.artist in seen:
            return f"{where} is listed twice"
        seen.add(row.artist)
    if len(rows) > TOP:
        return f"{len(rows)} rows, more than {TOP}"
    return None


def unsorted_at(rows):
    """The first position (1-based) whose row should come before the one above it, or None."""
    for position in range(1, len(rows)):
        here, above = rows[position], rows[position - 1]
        if (-here.listeners, here.artist) < (-above.listeners, above.artist):
            return position + 1
    return None
