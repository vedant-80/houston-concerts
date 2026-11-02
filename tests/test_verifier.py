"""The find-concerts verdict on the mini snapshot: one test per kind of answer the assignment names
(correct, incorrect, missing, malformed, boundary), each failing the check it should."""

from __future__ import annotations

from pathlib import Path

import pytest
from helpers import failing, gold_answer, judge, mutated, task
from slimconfig import build_output

import verifier
from contract import ArtistInput, ArtistOutput, FindInput, FindOutput, PinOutput

NOV = ("2026-11-02", "2026-11-30")
WINDOW = ("2026-11-02", "2026-12-02")
ACT_14 = {"artist": "Act 14", "listeners": 1000, "date": "2026-11-18", "venue": "The End"}
ACT_15 = {"artist": "Act 15", "listeners": 1000, "date": "2026-11-18", "venue": "The End"}

# Correct ----------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "dates",
    [NOV, WINDOW, ("2026-11-12", "2026-11-12"), ("2026-11-15", "2026-11-30"), ("2026-11-03", "2026-11-07")],
)
def test_the_gold_answer_holds_every_check(mini, tmp_path: Path, dates) -> None:
    verdict = judge(*dates, gold_answer(*dates, tmp_path), tmp_path)
    assert verdict["valid"] and verdict["score"] == 1.0, verdict["message"]
    assert all(entry["ok"] for entry in verdict["details"]["checks"])


# Incorrect --------------------------------------------------------------------------------------


def test_two_swapped_rows_fail_order_and_exact(mini, tmp_path: Path) -> None:
    def swap(answer):
        answer["concerts"][0], answer["concerts"][1] = answer["concerts"][1], answer["concerts"][0]

    verdict = mutated(*NOV, tmp_path, swap)
    assert failing(verdict) == ["order", "rows-exact"] and verdict["score"] == pytest.approx(18 / 20)


def test_a_later_show_instead_of_the_first_in_range_fails_exact(mini, tmp_path: Path) -> None:
    def later(answer):
        answer["concerts"][1].update(date="2026-11-20", venue="House of Blues Houston")

    verdict = mutated(*NOV, tmp_path, later)
    assert failing(verdict) == ["rows-exact"] and "Toyota Center" in verdict["message"]


def test_the_wrong_venue_fails_exact(mini, tmp_path: Path) -> None:
    def venue(answer):
        answer["concerts"][0]["venue"] = "Warehouse Live"

    assert failing(mutated("2026-11-12", "2026-11-12", tmp_path, venue)) == ["rows-exact"]


def test_wrong_listener_counts_fail_exact(mini, tmp_path: Path) -> None:
    def listeners(answer):
        answer["concerts"][3]["listeners"] = 300_001

    assert "rows-exact" in failing(mutated(*NOV, tmp_path, listeners))


def test_an_artist_playing_outside_the_range_fails_in_range_and_no_extra(mini, tmp_path: Path) -> None:
    def late(answer):
        answer["concerts"].insert(
            0, {"artist": "Late Show", "listeners": 9_999_999, "date": "2026-12-02", "venue": "White Oak Music Hall"}
        )
        answer["concerts"].pop()

    verdict = mutated(*NOV, tmp_path, late)
    assert {"in-range", "no-extra", "none-missing", "rows-exact"} <= set(failing(verdict))


def test_an_answer_for_other_dates_fails_range_and_scores_zero(mini, tmp_path: Path) -> None:
    verdict = judge(*NOV, gold_answer(*WINDOW, tmp_path), tmp_path)
    assert "range" in failing(verdict) and verdict["score"] == 0.0


def test_another_window_fails_window_and_scores_zero(mini, tmp_path: Path) -> None:
    def window(answer):
        answer["window"]["end"] = "2026-12-31"

    verdict = mutated(*NOV, tmp_path, window)
    assert failing(verdict) == ["window"] and verdict["score"] == 0.0


def test_a_wrong_total_fails_total(mini, tmp_path: Path) -> None:
    def total(answer):
        answer["total_artists"] = 20

    assert failing(mutated(*NOV, tmp_path, total)) == ["total"]


# Missing ----------------------------------------------------------------------------------------


def test_a_dropped_artist_fails_count_and_none_missing(mini, tmp_path: Path) -> None:
    def drop(answer):
        del answer["concerts"][3]

    assert {"count", "rows-exact", "none-missing"} <= set(failing(mutated(*NOV, tmp_path, drop)))


def test_an_empty_list_when_artists_play_fails(mini, tmp_path: Path) -> None:
    def empty(answer):
        answer["concerts"] = []

    verdict = mutated(*NOV, tmp_path, empty)
    assert {"count", "none-missing"} <= set(failing(verdict)) and verdict["score"] == 0.0


# Malformed --------------------------------------------------------------------------------------


@pytest.mark.parametrize("date", ["Nov 10", "2026-11-31", "2026-13-01", "2026-11-1", ""])
def test_a_date_that_is_not_a_calendar_date_is_malformed(mini, tmp_path: Path, date: str) -> None:
    def spoil(answer):
        answer["concerts"][0]["date"] = date

    verdict = mutated(*NOV, tmp_path, spoil)
    assert "well-formed" in failing(verdict)
    order = next(entry for entry in verdict["details"]["checks"] if entry["id"] == "order")
    assert order["ok"] is None, "order is skipped, never a crash, on a malformed list"


def test_twenty_one_rows_fail_well_formed_and_count(mini, tmp_path: Path) -> None:
    def add(answer):
        answer["concerts"].append(ACT_15)

    assert {"well-formed", "count", "no-extra"} <= set(failing(mutated(*NOV, tmp_path, add)))


def test_a_duplicate_artist_fails_well_formed(mini, tmp_path: Path) -> None:
    def duplicate(answer):
        answer["concerts"][2] = answer["concerts"][1]

    assert "well-formed" in failing(mutated(*NOV, tmp_path, duplicate))


def test_negative_listeners_are_malformed(mini, tmp_path: Path) -> None:
    def negative(answer):
        answer["concerts"][0]["listeners"] = -1

    assert "well-formed" in failing(mutated(*NOV, tmp_path, negative))


def test_a_value_of_the_wrong_type_is_refused_before_the_verifier() -> None:
    with pytest.raises(ValueError):
        build_output(
            {**task(*NOV), "window": {"start": "a", "end": "b"}, "total_artists": "26", "concerts": []}, FindOutput
        )


@pytest.mark.parametrize(
    "dates", [("2026-11-30", "2026-11-02"), ("2026-02-29", "2026-03-01"), ("11/02/2026", "2026-11-30"), ("", "")]
)
def test_malformed_ranges_are_refused_as_input(dates) -> None:
    for tool in ("find_concerts", "pin_concerts"):
        assert verifier.verify_input(tool, build_output(task(*dates), FindInput))["valid"] is False


def test_a_real_leap_day_is_a_valid_input() -> None:
    assert verifier.verify_input("find_concerts", build_output(task("2028-02-29", "2028-03-01"), FindInput))["valid"]


# Boundary ---------------------------------------------------------------------------------------


def test_both_ends_of_the_range_count(mini, tmp_path: Path) -> None:
    assert [row["artist"] for row in gold_answer("2026-11-02", "2026-11-02", tmp_path)["concerts"]] == ["Mid Band"]
    assert [row["artist"] for row in gold_answer("2026-12-02", "2026-12-02", tmp_path)["concerts"]] == ["Late Show"]


def test_the_other_side_of_a_tie_at_the_cut_fails(mini, tmp_path: Path) -> None:
    def other(answer):
        answer["concerts"][-1] = ACT_15

    verdict = mutated(*NOV, tmp_path, other)
    assert {"rows-exact", "no-extra", "none-missing"} <= set(failing(verdict))
    assert "order" not in failing(verdict), "still sorted; it holds the wrong artist of the tie"
    assert gold_answer(*NOV, tmp_path)["concerts"][-1] == ACT_14


def test_tied_listeners_in_the_wrong_name_order_fail_order(mini, tmp_path: Path) -> None:
    def swap(answer):
        answer["concerts"][3], answer["concerts"][4] = answer["concerts"][4], answer["concerts"][3]

    assert "order" in failing(mutated(*NOV, tmp_path, swap))


def test_same_day_shows_need_the_earliest_start(mini, tmp_path: Path) -> None:
    def later_start(answer):
        answer["concerts"][0]["venue"] = "Warehouse Live"

    assert gold_answer("2026-11-12", "2026-11-12", tmp_path)["concerts"][0]["venue"] == "Bayou Music Center"
    assert "rows-exact" in failing(mutated("2026-11-12", "2026-11-12", tmp_path, later_start))


def test_nothing_playing_needs_an_empty_answer(mini, tmp_path: Path) -> None:
    empty = ("2026-11-03", "2026-11-07")
    answer = gold_answer(*empty, tmp_path)
    assert answer["concerts"] == [] and judge(*empty, answer, tmp_path)["valid"]
    wrong = gold_answer("2026-11-02", "2026-11-08", tmp_path) | task(*empty)
    assert {"count", "no-extra", "in-range", "total"} <= set(failing(judge(*empty, wrong, tmp_path)))


# The answer key and tool outputs ----------------------------------------------------------------


def test_no_answer_key_fails_first_and_scores_zero(mini, tmp_path: Path) -> None:
    output = build_output(gold_answer(*NOV, tmp_path), FindOutput)
    verdict = verifier.verify_task("find-concerts", build_output(task(*NOV), FindInput), output, None, "")
    assert failing(verdict) == ["answer-key"] and verdict["score"] == 0.0


def test_an_answer_key_with_a_show_outside_its_window_is_refused() -> None:
    pin = build_output(
        {
            **task(*NOV),
            "window": {"start": "2026-11-02", "end": "2026-12-02"},
            "shows": [{"artist": "A", "date": "2027-01-01", "time": "", "venue": "V", "event_id": "X"}],
            "listeners": [{"artist": "A", "listeners": 1}],
        },
        PinOutput,
    )
    verdict = verifier.verify_output("pin_concerts", build_output(task(*NOV), FindInput), pin, "")
    assert verdict["valid"] is False and "outside the window" in verdict["message"]


def test_an_artist_shows_answer_out_of_date_order_is_refused() -> None:
    out = build_output(
        {
            "artist": "A",
            "found": True,
            "listeners": 1,
            "window": {"start": "2026-11-02", "end": "2026-12-02"},
            "shows": [
                {"artist": "A", "date": "2026-11-20", "time": "", "venue": "V", "event_id": "X"},
                {"artist": "A", "date": "2026-11-10", "time": "", "venue": "V", "event_id": "Y"},
            ],
        },
        ArtistOutput,
    )
    verdict = verifier.verify_output("artist_shows", build_output({"artist": "a"}, ArtistInput), out, "")
    assert verdict["valid"] is False and "earliest first" in verdict["message"]
