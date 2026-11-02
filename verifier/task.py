"""The find-concerts verdict: named checks, in order, comparing the submitted answer with the rows the
verifier derives itself from the answer key's full list of shows, whatever their dates.

The verdict is valid only when every check holds. Any failure among GATES (the answer key, the date
range, the window) scores 0; otherwise the score is the share of ranks whose row is exactly right, out
of the longer of the expected and the submitted list (1.0 when both are empty)."""

from .checks import constraint, first_failure, named, result
from .pin import pin_problem
from .rules import TOP, expected_rows, plain, rows_problem, unsorted_at

TEXT = {
    "answer-key": "The answer key is pinned for this date range and well formed",
    "range": "The answer is for the task's start and end dates",
    "window": "The answer names the snapshot's window of dates",
    "well-formed": "Every row has an artist, listeners >= 0 and a calendar date, once per artist, at most 20",
    "count": "The answer lists min(20, artists playing in the range) rows",
    "order": "Rows are ranked by Last.fm listeners, most first, ties alphabetically by artist",
    "rows-exact": "At each rank, the artist, listeners, date and venue of their first show in the range are exactly the expected ones",
    "no-extra": "No artist outside the expected top 20 is listed",
    "none-missing": "Every artist in the expected top 20 is listed",
    "in-range": "Every listed show falls between the start and end dates",
    "total": "total_artists counts every artist playing in the range",
}
GATES = ("answer-key", "range", "window")


def verify_task(arguments, output, reference, workspace):
    entries = []

    def check(identifier, ok, expected=None, actual=None, message=""):
        entries.append(constraint(identifier, TEXT[identifier], ok, expected, actual, message))
        return ok

    problem = pin_problem(arguments, reference)
    if not check("answer-key", problem is None, message=problem or ""):
        return verdict(entries, 0.0)
    first, last = arguments.start_date, arguments.end_date
    check(
        "range",
        (output.start_date, output.end_date) == (first, last),
        [first, last],
        [output.start_date, output.end_date],
        f"the answer is for {output.start_date} to {output.end_date}, the task for {first} to {last}",
    )
    want_window = {"start": reference.window.start, "end": reference.window.end}
    got_window = {"start": output.window.start, "end": output.window.end}
    check("window", got_window == want_window, want_window, got_window, "the window is not the snapshot's")

    every = expected_rows(reference, first, last)
    expected = every[:TOP]
    malformed = rows_problem(output.concerts)
    check("well-formed", malformed is None, message=malformed or "")
    check(
        "count",
        len(output.concerts) == len(expected),
        len(expected),
        len(output.concerts),
        f"{len(output.concerts)} rows listed; {len(every)} artists play then, so {len(expected)} must be",
    )
    position = None if malformed else unsorted_at(output.concerts)
    check(
        "order",
        None if malformed else position is None,
        message=(
            "skipped: the list is malformed"
            if malformed
            else f"row #{position} ({output.concerts[position - 1].artist}) ranks above #{position - 1}"
            if position
            else ""
        ),
    )
    wrong, correct = [], 0
    for rank in range(max(len(expected), len(output.concerts))):
        want = expected[rank] if rank < len(expected) else None
        got = plain(output.concerts[rank]) if rank < len(output.concerts) else None
        if want == got:
            correct += 1
        else:
            wrong.append(f"#{rank + 1} expected {want or 'nothing'} got {got or 'nothing'}")
    check("rows-exact", not wrong, actual=f"{correct} of {len(expected)} ranks right", message=named(wrong))
    wanted = [row["artist"] for row in expected]
    listed = [row.artist for row in output.concerts]
    extra = [artist for artist in listed if artist not in wanted]
    missing = [artist for artist in wanted if artist not in listed]
    check("no-extra", not extra, [], extra, f"not in the expected top {TOP}: {named(extra)}")
    check("none-missing", not missing, [], missing, f"missing from the answer: {named(missing)}")
    outside = [row.artist for row in output.concerts if not first <= row.date <= last]
    check("in-range", not outside, [], outside, f"listed with a date outside {first} to {last}: {named(outside)}")
    check(
        "total",
        output.total_artists == len(every),
        len(every),
        output.total_artists,
        f"total_artists is {output.total_artists}; {len(every)} artists play then",
    )

    gated = any(entry["ok"] is False for entry in entries if entry["id"] in GATES)
    longest = max(len(expected), len(output.concerts))
    score = 0.0 if gated else (correct / longest if longest else 1.0)
    return verdict(entries, score)


def verdict(entries, score):
    for entry in entries:
        if entry["ok"]:
            entry["message"] = ""
    failure = first_failure(entries)
    if failure is None:
        return result(True, f"all {len(entries)} checks hold", score=1.0, checks=entries)
    return result(False, failure, score=score, checks=entries)
