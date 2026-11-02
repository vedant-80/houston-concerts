"""A small hand-made snapshot whose answers are known, and a fixture that makes every tool read it.

Window 2026-11-02 to 2026-12-02. From 2026-11-02 to 2026-11-30, 26 artists play:
Mega (9,000,000 listeners), Big Star (two shows: its first in that range is 11-10 at Toyota Center,
but from 11-15 on it is 11-20 at House of Blues), Mid Band (the window's first day), Tie A and Tie B
(equal listeners), Same Day (three shows on 11-12: 21:00, 19:00 and an unannounced time; 19:00 is the
first) and Act 01 ... Act 20 (all 1,000 listeners, so the cut at 20 falls inside an alphabetical tie).
Late Show plays only on the window's last day, 12-02. Nobody plays 11-03 to 11-07."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from plugin import snapshot as snapshot_module
from plugin import tools

WINDOW = {"start": "2026-11-02", "end": "2026-12-02"}
LISTENERS = {
    "Mega": 9_000_000,
    "Big Star": 5_000_000,
    "Mid Band": 1_000_000,
    "Tie A": 300_000,
    "Tie B": 300_000,
    "Same Day": 200_000,
    "Late Show": 100_000,
    **{f"Act {n:02d}": 1_000 for n in range(1, 21)},
}


def show(event_id: str, artist: str, date: str, venue: str = "White Oak Music Hall", time: str = "20:00"):
    return {"event_id": event_id, "artist": artist, "date": date, "time": time, "venue": venue}


SHOWS = [
    show("E1", "Mega", "2026-11-28", "NRG Stadium"),
    show("E2", "Big Star", "2026-11-20", "House of Blues Houston"),
    show("E3", "Big Star", "2026-11-10", "Toyota Center"),
    show("E4", "Mid Band", "2026-11-02", "713 Music Hall"),
    show("E5", "Tie A", "2026-11-08"),
    show("E6", "Tie B", "2026-11-09"),
    show("E7", "Same Day", "2026-11-12", "Warehouse Live", time="21:00"),
    show("E8", "Same Day", "2026-11-12", "Bayou Music Center", time="19:00"),
    show("E9", "Same Day", "2026-11-12", "The End", time=""),
    show("E10", "Late Show", "2026-12-02"),
    *[show(f"F{n}", f"Act {n:02d}", "2026-11-18", "The End") for n in range(1, 21)],
]


@pytest.fixture
def mini(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> snapshot_module.Snapshot:
    data = {"window": WINDOW, "fetched_at": "2026-11-02T06:00:00Z", "shows": SHOWS, "listeners": LISTENERS}
    path = tmp_path / "mini.json.gz"
    path.write_bytes(gzip.compress(json.dumps(data).encode()))
    loaded = snapshot_module.load.__wrapped__(path)
    monkeypatch.setattr(tools, "load", lambda: loaded)
    return loaded
