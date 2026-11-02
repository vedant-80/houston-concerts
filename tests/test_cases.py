"""End-to-end cases on the real snapshot: the reference tool, the scripted agent's call and the
verdict, with no model. These are the runs the report cites; -v prints each case's name."""

from __future__ import annotations

import copy
from datetime import date, timedelta
from pathlib import Path

import pytest
from helpers import failing, gold_answer, judge

from contract import ArtistInput
from plugin import artist_shows
from plugin.snapshot import load

SNAPSHOT = load()
START = date.fromisoformat(SNAPSHOT.start)


def days(first: int, last: int) -> tuple[str, str]:
    return ((START + timedelta(days=first)).isoformat(), (START + timedelta(days=last)).isoformat())


RANGES = {"whole-window": days(0, 30), "first-week": days(0, 6), "second-week": days(7, 13), "first-day": days(0, 0)}


@pytest.mark.parametrize("dates", RANGES.values(), ids=list(RANGES))
def test_gold_run_holds_every_check(tmp_path: Path, dates) -> None:
    verdict = judge(*dates, gold_answer(*dates, tmp_path), tmp_path)
    assert verdict["valid"] and verdict["score"] == 1.0, verdict["message"]


def test_the_whole_window_finds_every_artist(tmp_path: Path) -> None:
    assert gold_answer(*days(0, 30), tmp_path)["total_artists"] == len(SNAPSHOT.listeners)


def test_each_listed_show_is_the_artists_first_in_the_range(tmp_path: Path) -> None:
    first, last = days(7, 20)
    for row in gold_answer(first, last, tmp_path)["concerts"]:
        shows = [s for s in artist_shows(ArtistInput(artist=row["artist"]), tmp_path).shows if first <= s.date <= last]
        assert (shows[0].date, shows[0].venue) == (row["date"], row["venue"]), row["artist"]


@pytest.mark.parametrize(
    ("name", "change", "fails"),
    [
        ("reversed", lambda a: a["concerts"].reverse(), {"order", "rows-exact"}),
        ("top3-only", lambda a: a["concerts"].__delitem__(slice(3, None)), {"count", "none-missing"}),
        (
            "listeners-off-by-one",
            lambda a: [r.update(listeners=r["listeners"] + 1) for r in a["concerts"]],
            {"rows-exact"},
        ),
        ("other-dates", lambda a: a.update(start_date="2026-01-01"), {"range"}),
    ],
)
def test_wrong_answers_fail_their_check(tmp_path: Path, name: str, change, fails: set[str]) -> None:
    answer = copy.deepcopy(gold_answer(*days(0, 30), tmp_path))
    if len(answer["concerts"]) < 4:
        pytest.skip("fewer than 4 artists in this snapshot")
    change(answer)
    verdict = judge(*days(0, 30), answer, tmp_path)
    assert not verdict["valid"] and fails <= set(failing(verdict)), (name, verdict["message"])
