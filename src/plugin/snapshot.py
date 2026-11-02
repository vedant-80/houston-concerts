"""The frozen concert snapshot (data/concerts.json.gz) and the ranking every tool shares."""

from __future__ import annotations

import gzip
import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path

SNAPSHOT = Path(__file__).resolve().parent / "data" / "concerts.json.gz"
TOP = 20


@dataclass(frozen=True)
class Snapshot:
    start: str
    end: str
    shows: tuple[dict, ...]  # each {event_id, artist, date, time, venue}
    listeners: dict[str, int]


@cache
def load(path: Path = SNAPSHOT) -> Snapshot:
    data = json.loads(gzip.decompress(path.read_bytes()))
    return Snapshot(
        start=data["window"]["start"],
        end=data["window"]["end"],
        shows=tuple(data["shows"]),
        listeners=data["listeners"],
    )


def show_order(show: dict) -> tuple:
    """Shows in time order: date, then start time (unannounced last), then event id."""
    return (show["date"], show["time"] or "99:99", show["event_id"])


def ranked_artists(snapshot: Snapshot, first: str, last: str) -> list[dict]:
    """One row per artist headlining a show from ``first`` to ``last`` (inclusive): their first show in
    that range, most listeners first, ties alphabetically by artist."""
    earliest: dict[str, dict] = {}
    for show in snapshot.shows:
        if not first <= show["date"] <= last:
            continue
        best = earliest.get(show["artist"])
        if best is None or show_order(show) < show_order(best):
            earliest[show["artist"]] = show
    rows = [
        {"artist": artist, "listeners": snapshot.listeners[artist], "date": show["date"], "venue": show["venue"]}
        for artist, show in earliest.items()
    ]
    return sorted(rows, key=lambda row: (-row["listeners"], row["artist"]))
