"""find_concerts, artist_shows and pin_concerts on the mini snapshot, whose answers are worked out by hand."""

from __future__ import annotations

from pathlib import Path

import pytest

from contract import ArtistInput, FindInput
from plugin import artist_shows, find_concerts, pin_concerts

NOVEMBER = ("2026-11-02", "2026-11-30")


def rows(first: str, last: str, tmp_path: Path):
    return find_concerts(FindInput(start_date=first, end_date=last), tmp_path)


def test_artists_rank_by_listeners_then_name(mini, tmp_path: Path) -> None:
    out = rows(*NOVEMBER, tmp_path)
    assert [row.artist for row in out.concerts[:7]] == [
        "Mega",
        "Big Star",
        "Mid Band",
        "Tie A",
        "Tie B",
        "Same Day",
        "Act 01",
    ]


def test_each_artist_shows_their_first_show_in_the_range(mini, tmp_path: Path) -> None:
    big = rows(*NOVEMBER, tmp_path).concerts[1]
    assert (big.date, big.venue) == ("2026-11-10", "Toyota Center")
    later = rows("2026-11-15", "2026-11-30", tmp_path).concerts[1]
    assert (later.artist, later.date, later.venue) == ("Big Star", "2026-11-20", "House of Blues Houston")


def test_shows_on_one_day_keep_the_earliest_start_and_an_unannounced_time_last(mini, tmp_path: Path) -> None:
    out = rows("2026-11-12", "2026-11-12", tmp_path)
    assert [(row.artist, row.venue) for row in out.concerts] == [("Same Day", "Bayou Music Center")]


def test_both_ends_of_the_range_are_included(mini, tmp_path: Path) -> None:
    assert [row.artist for row in rows("2026-11-02", "2026-11-02", tmp_path).concerts] == ["Mid Band"]
    assert [row.artist for row in rows("2026-12-02", "2026-12-02", tmp_path).concerts] == ["Late Show"]
    assert "Late Show" not in [row.artist for row in rows(*NOVEMBER, tmp_path).concerts]


def test_more_than_twenty_artists_are_cut_to_twenty_and_counted(mini, tmp_path: Path) -> None:
    out = rows(*NOVEMBER, tmp_path)
    assert out.total_artists == 26 and len(out.concerts) == 20
    assert out.concerts[-1].artist == "Act 14", "the cut falls inside the 1,000-listener tie, alphabetically"


def test_a_range_with_no_shows_finds_nothing(mini, tmp_path: Path) -> None:
    out = rows("2026-11-03", "2026-11-07", tmp_path)
    assert out.total_artists == 0 and out.concerts == []


@pytest.mark.parametrize(
    ("first", "last", "words"),
    [
        ("2026-11-10", "2026-11-05", "after"),
        ("2026-11-01", "2026-11-05", "window"),
        ("2026-11-20", "2026-12-03", "window"),
        ("2026-02-30", "2026-03-01", "calendar date"),
        ("11/10/2026", "2026-11-12", "calendar date"),
        ("", "2026-11-12", "calendar date"),
    ],
)
def test_a_bad_range_is_refused_by_name(mini, tmp_path: Path, first: str, last: str, words: str) -> None:
    with pytest.raises(ValueError, match=words):
        rows(first, last, tmp_path)


def test_artist_shows_lists_every_show_earliest_first(mini, tmp_path: Path) -> None:
    out = artist_shows(ArtistInput(artist="same day"), tmp_path)
    assert out.found and out.artist == "Same Day" and [s.time for s in out.shows] == ["19:00", "21:00", ""]


def test_an_unknown_artist_is_not_found(mini, tmp_path: Path) -> None:
    out = artist_shows(ArtistInput(artist="Nobody"), tmp_path)
    assert not out.found and out.shows == [] and out.listeners == 0


def test_the_answer_key_holds_every_show_whatever_the_range(mini, tmp_path: Path) -> None:
    pin = pin_concerts(FindInput(start_date="2026-11-12", end_date="2026-11-12"), tmp_path)
    assert len(pin.shows) == 30 and len(pin.listeners) == 27
