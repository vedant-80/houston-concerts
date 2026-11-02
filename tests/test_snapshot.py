"""The shipped snapshot is the one SOURCE.json records, and every show in it is well formed."""

from __future__ import annotations

import hashlib
import json
import re

from plugin.snapshot import SNAPSHOT, load

SOURCE = json.loads((SNAPSHOT.parent / "SOURCE.json").read_text(encoding="utf-8"))


def test_the_snapshot_is_the_one_source_json_records() -> None:
    assert hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest() == SOURCE["outputs"][SNAPSHOT.name]
    assert {"start": load().start, "end": load().end} == SOURCE["window"]


def test_every_show_is_in_the_window_and_by_an_artist_with_listeners() -> None:
    snapshot = load()
    assert snapshot.shows, "the snapshot holds no shows"
    for show in snapshot.shows:
        assert snapshot.start <= show["date"] <= snapshot.end, show
        assert re.fullmatch(r"(\d{2}:\d{2})?", show["time"]), show
        assert show["artist"] in snapshot.listeners, show
    assert len({show["event_id"] for show in snapshot.shows}) == len(snapshot.shows)


def test_the_counts_add_up() -> None:
    assert SOURCE["counts"]["kept: shows"] == len(load().shows)
    assert SOURCE["counts"]["kept: artists"] == len(load().listeners)


def test_the_snapshot_is_small_enough_to_publish() -> None:
    assert SNAPSHOT.stat().st_size < 2_000_000
