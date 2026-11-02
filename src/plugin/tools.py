"""The three tools: each takes its contract input and the workspace (unused: they only read the
snapshot) and returns its contract output."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from contract import (
    ArtistInput,
    ArtistListeners,
    ArtistOutput,
    ConcertRow,
    FindInput,
    FindOutput,
    PinOutput,
    Show,
    Window,
)
from plugin.snapshot import TOP, Snapshot, load, ranked_artists, show_order

DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def range_of(given: FindInput, snapshot: Snapshot) -> tuple[str, str]:
    """The search range as given, or ValueError naming what is wrong and the window it must fit."""
    for name in ("start_date", "end_date"):
        text = getattr(given, name)
        try:
            ok = bool(DATE.fullmatch(text)) and date.fromisoformat(text).isoformat() == text
        except ValueError:
            ok = False
        if not ok:
            raise ValueError(f"{name} {text!r} is not a calendar date YYYY-MM-DD")
    if given.start_date > given.end_date:
        raise ValueError(f"start_date {given.start_date} is after end_date {given.end_date}")
    if given.start_date < snapshot.start or given.end_date > snapshot.end:
        raise ValueError(
            f"{given.start_date} to {given.end_date} is not inside the snapshot's window, {snapshot.start} to {snapshot.end}"
        )
    return given.start_date, given.end_date


def find_concerts(given: FindInput, workspace: Path) -> FindOutput:
    snapshot = load()
    rows = ranked_artists(snapshot, *range_of(given, snapshot))
    return FindOutput(
        start_date=given.start_date,
        end_date=given.end_date,
        window=Window(start=snapshot.start, end=snapshot.end),
        total_artists=len(rows),
        concerts=[ConcertRow(**row) for row in rows[:TOP]],
    )


def artist_shows(given: ArtistInput, workspace: Path) -> ArtistOutput:
    snapshot = load()
    window = Window(start=snapshot.start, end=snapshot.end)
    wanted = given.artist.strip().casefold()
    names = [artist for artist in snapshot.listeners if artist.casefold() == wanted]
    if not names:
        return ArtistOutput(artist=given.artist, found=False, listeners=0, window=window, shows=[])
    artist = names[0]
    shows = sorted((show for show in snapshot.shows if show["artist"] == artist), key=show_order)
    return ArtistOutput(
        artist=artist,
        found=True,
        listeners=snapshot.listeners[artist],
        window=window,
        shows=[Show(**show) for show in shows],
    )


def pin_concerts(given: FindInput, workspace: Path) -> PinOutput:
    """The answer key: every show in the window and every headliner's listeners, whatever the range."""
    snapshot = load()
    range_of(given, snapshot)
    return PinOutput(
        start_date=given.start_date,
        end_date=given.end_date,
        window=Window(start=snapshot.start, end=snapshot.end),
        shows=[Show(**show) for show in snapshot.shows],
        listeners=[ArtistListeners(artist=artist, listeners=count) for artist, count in snapshot.listeners.items()],
    )
