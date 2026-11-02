"""Run a find-concerts task the way NanoAgent does, with a script in place of the model: the reference
tool first, then find_concerts, each call checked by verify_input and verify_output, then verify_task."""

from __future__ import annotations

import copy
from pathlib import Path

from slimconfig import build_output, plain_output

import verifier
from contract import FindInput, FindOutput
from plugin import find_concerts, pin_concerts


def call(tool: str, implementation, given_class, arguments: dict, workspace: Path):
    given = build_output(arguments, given_class)
    assert verifier.verify_input(tool, given)["valid"], verifier.verify_input(tool, given)
    made = implementation(given, workspace)
    verdict = verifier.verify_output(tool, given, made, str(workspace))
    assert verdict["valid"], verdict
    return made


def task(first: str, last: str) -> dict:
    return {"start_date": first, "end_date": last}


def gold_answer(first: str, last: str, workspace: Path) -> dict:
    """The answer the task's instructions give: find_concerts' result, unchanged."""
    return plain_output(call("find_concerts", find_concerts, FindInput, task(first, last), workspace))


def judge(first: str, last: str, answer: dict, workspace: Path) -> dict:
    """The verdict for ``answer`` to a task for ``first`` to ``last``, against the pinned answer key."""
    arguments = build_output(task(first, last), FindInput)
    reference = call("pin_concerts", pin_concerts, FindInput, task(first, last), workspace)
    output = build_output(answer, FindOutput)
    first_verdict = verifier.verify_task("find-concerts", arguments, output, reference, str(workspace))
    second = verifier.verify_task(
        "find-concerts", arguments, copy.deepcopy(output), copy.deepcopy(reference), str(workspace)
    )
    assert first_verdict == second, "the verdict must be deterministic"
    return first_verdict


def failing(verdict: dict) -> list[str]:
    return [entry["id"] for entry in verdict["details"]["checks"] if entry["ok"] is False]


def mutated(first: str, last: str, workspace: Path, change) -> dict:
    answer = copy.deepcopy(gold_answer(first, last, workspace))
    change(answer)
    return judge(first, last, answer, workspace)
