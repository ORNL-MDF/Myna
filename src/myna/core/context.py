#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Workflow context shared between Myna workflow orchestration and apps."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class WorkflowContext:
    """Explicit workflow state for an active Myna operation."""

    input_file: str | None = None
    step_name: str | None = None
    step_class: str | None = None
    step_index: int | None = None
    last_step_name: str | None = None
    last_step_class: str | None = None


_CURRENT_WORKFLOW_CONTEXT: ContextVar[WorkflowContext | None] = ContextVar(
    "myna_current_workflow_context", default=None
)


def current_workflow_context() -> WorkflowContext | None:
    """Return the active workflow context, if one has been set."""

    return _CURRENT_WORKFLOW_CONTEXT.get()


@contextmanager
def workflow_context(
    *,
    input_file: str | None = None,
    step_name: str | None = None,
    step_class: str | None = None,
    step_index: int | None = None,
    last_step_name: str | None = None,
    last_step_class: str | None = None,
):
    """Temporarily set explicit workflow state for in-process app execution."""

    parent = current_workflow_context()
    context = WorkflowContext(
        input_file=(
            input_file
            if input_file is not None
            else _parent_value(parent, "input_file")
        ),
        step_name=(
            step_name if step_name is not None else _parent_value(parent, "step_name")
        ),
        step_class=(
            step_class
            if step_class is not None
            else _parent_value(parent, "step_class")
        ),
        step_index=(
            step_index
            if step_index is not None
            else _parent_value(parent, "step_index")
        ),
        last_step_name=last_step_name
        if last_step_name is not None
        else _parent_value(parent, "last_step_name"),
        last_step_class=last_step_class
        if last_step_class is not None
        else _parent_value(parent, "last_step_class"),
    )
    token = _CURRENT_WORKFLOW_CONTEXT.set(context)
    try:
        yield context
    finally:
        _CURRENT_WORKFLOW_CONTEXT.reset(token)


def get_workflow_input_file(default: str | None = None) -> str | None:
    """Return the active workflow input file, falling back to legacy env state."""

    context = current_workflow_context()
    if context is not None and context.input_file is not None:
        return context.input_file
    return os.environ.get("MYNA_INPUT", default)


def _parent_value(parent: WorkflowContext | None, field: str):
    if parent is None:
        return None
    return getattr(parent, field)
