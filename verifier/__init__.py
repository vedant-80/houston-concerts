"""The deterministic verifier: each tool's checks live in its own module, on contract instances."""

from contract import Task, Tool

from . import find, pin, shows, task

TOOLS = {Tool.FIND_CONCERTS: find, Tool.ARTIST_SHOWS: shows, Tool.PIN_CONCERTS: pin}
# task -> its verdict, verify_task(arguments, output, reference, workspace)
TASKS = {Task.FIND_CONCERTS: task.verify_task, Task.ARTIST_SHOWS: shows.verify_task}


def verify_input(tool, value):
    return TOOLS[Tool(tool)].verify_input(value)


def verify_output(tool, input_value, output_value, workspace):
    return TOOLS[Tool(tool)].verify_output(input_value, output_value, workspace)


def verify_task(task_id, arguments, output, reference, workspace):
    return TASKS[Task(task_id)](arguments, output, reference, workspace)
