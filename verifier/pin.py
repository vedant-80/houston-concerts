"""pin_concerts, the answer key: well-formed shows inside the window, each headliner with a listener count."""

from .checks import result
from .rules import is_date, range_problem, show_problem


def verify_input(value):
    problem = range_problem(value.start_date, value.end_date)
    return result(problem is None, problem or "the date range is valid")


def pin_problem(arguments, pin):
    """What is wrong with an answer key for the task ``arguments``, or None."""
    if pin is None:
        return "there is no answer key: NanoAgent pins pin_concerts before the agent starts"
    if (pin.start_date, pin.end_date) != (arguments.start_date, arguments.end_date):
        return f"the answer key is for {pin.start_date} to {pin.end_date}, not {arguments.start_date} to {arguments.end_date}"
    start, end = pin.window.start, pin.window.end
    if not is_date(start) or not is_date(end) or start > end:
        return f"the answer key's window {start!r} to {end!r} is not a range of dates"
    if arguments.start_date < start or arguments.end_date > end:
        return f"{arguments.start_date} to {arguments.end_date} is not inside the window, {start} to {end}"
    known = {}
    for entry in pin.listeners:
        if entry.artist in known or entry.listeners < 0:
            return f"the answer key lists {entry.artist!r} twice or with a negative count"
        known[entry.artist] = entry.listeners
    ids = set()
    for show in pin.shows:
        problem = show_problem(show, start, end)
        if problem:
            return f"the answer key's {problem}"
        if show.event_id in ids:
            return f"the answer key lists show {show.event_id} twice"
        ids.add(show.event_id)
        if show.artist not in known:
            return f"the answer key's show {show.event_id} is by {show.artist!r}, who has no listener count"
    return None


def verify_output(input_value, output_value, workspace):
    problem = pin_problem(input_value, output_value)
    return result(problem is None, problem or f"the answer key holds {len(output_value.shows)} shows")
