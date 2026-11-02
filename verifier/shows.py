"""artist_shows (and the artist-shows task, which is that one tool): one artist's shows, well formed and in order."""

from .checks import result
from .rules import show_order, show_problem


def verify_input(value):
    if not value.artist.strip() or len(value.artist) > 200:
        return result(False, "the artist is blank or longer than 200 characters")
    return result(True, "the artist is valid")


def verify_output(input_value, output_value, workspace):
    if not output_value.found:
        if output_value.shows or output_value.listeners or output_value.artist != input_value.artist:
            return result(False, "a not-found answer must echo the artist and have no shows and 0 listeners")
        return result(True, f"{input_value.artist!r} headlines no show in the window")
    if output_value.artist.casefold() != input_value.artist.strip().casefold():
        return result(False, f"the answer is about {output_value.artist!r}, not {input_value.artist!r}")
    if not output_value.shows:
        return result(False, "a found artist must have at least one show")
    for show in output_value.shows:
        problem = show_problem(show, output_value.window.start, output_value.window.end)
        if problem:
            return result(False, problem)
        if show.artist != output_value.artist:
            return result(False, f"show {show.event_id} is by {show.artist}, not {output_value.artist}")
    keys = [show_order(show) for show in output_value.shows]
    if keys != sorted(keys) or len({show.event_id for show in output_value.shows}) != len(keys):
        return result(False, "the shows are not each listed once, earliest first")
    return result(True, f"{len(keys)} show(s) by {output_value.artist}, earliest first")


def verify_task(arguments, output, reference, workspace):
    return verify_output(arguments, output, workspace)
