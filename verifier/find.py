"""find_concerts: the top rows are well formed, inside the range, ranked, and the count adds up."""

from .checks import result
from .rules import TOP, range_problem, rows_problem, unsorted_at


def verify_input(value):
    problem = range_problem(value.start_date, value.end_date)
    return result(problem is None, problem or "the date range is valid")


def verify_output(input_value, output_value, workspace):
    asked = (input_value.start_date, input_value.end_date)
    if (output_value.start_date, output_value.end_date) != asked:
        return result(
            False,
            f"the output is for {output_value.start_date} to {output_value.end_date}, not {asked[0]} to {asked[1]}",
        )
    problem = rows_problem(output_value.concerts)
    if problem:
        return result(False, problem)
    outside = [row.artist for row in output_value.concerts if not asked[0] <= row.date <= asked[1]]
    if outside:
        return result(False, f"{', '.join(outside)} play outside {asked[0]} to {asked[1]}")
    expected = min(TOP, output_value.total_artists)
    if len(output_value.concerts) != expected:
        return result(
            False,
            f"{len(output_value.concerts)} rows; {output_value.total_artists} artists play then, so {expected} must be",
        )
    position = unsorted_at(output_value.concerts)
    if position:
        return result(False, f"row #{position} ({output_value.concerts[position - 1].artist}) is out of order")
    return result(True, f"the top {expected} of {output_value.total_artists} artists, ranked")
