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
import warnings


WORKFLOW_ENV_INPUT_FILE = "MYNA_INPUT"
WORKFLOW_ENV_RUN_INPUT = "MYNA_RUN_INPUT"
WORKFLOW_ENV_SYNC_INPUT = "MYNA_SYNC_INPUT"
WORKFLOW_ENV_STEP_NAME = "MYNA_STEP_NAME"
WORKFLOW_ENV_STEP_CLASS = "MYNA_STEP_CLASS"
WORKFLOW_ENV_STEP_INDEX = "MYNA_STEP_INDEX"
WORKFLOW_ENV_LAST_STEP_NAME = "MYNA_LAST_STEP_NAME"
WORKFLOW_ENV_LAST_STEP_CLASS = "MYNA_LAST_STEP_CLASS"


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
_LEGACY_ENV_FALLBACK_WARNED = False


def current_workflow_context() -> WorkflowContext | None:
    """Return the active workflow context, if one has been set."""

    return _CURRENT_WORKFLOW_CONTEXT.get()


def get_workflow_context() -> WorkflowContext | None:
    """Return explicit workflow context or derive it from legacy env vars."""

    context = current_workflow_context()
    if context is not None:
        return context

    if not _has_legacy_workflow_env():
        return None

    _warn_legacy_env_fallback()

    env_context = WorkflowContext(
        input_file=os.environ.get(WORKFLOW_ENV_INPUT_FILE),
        step_name=os.environ.get(WORKFLOW_ENV_STEP_NAME),
        step_class=os.environ.get(WORKFLOW_ENV_STEP_CLASS),
        step_index=_parse_optional_int(os.environ.get(WORKFLOW_ENV_STEP_INDEX)),
        last_step_name=os.environ.get(WORKFLOW_ENV_LAST_STEP_NAME),
        last_step_class=os.environ.get(WORKFLOW_ENV_LAST_STEP_CLASS),
    )
    return env_context


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

    context = get_workflow_context()
    if context is not None and context.input_file is not None:
        return context.input_file
    return default


@contextmanager
def workflow_env(
    context: WorkflowContext | None = None, *, operation: str | None = None
):
    """Temporarily expose workflow state through legacy environment variables."""

    if context is None:
        context = get_workflow_context()

    updates = {
        WORKFLOW_ENV_INPUT_FILE: None if context is None else context.input_file,
        WORKFLOW_ENV_STEP_NAME: None if context is None else context.step_name,
        WORKFLOW_ENV_STEP_CLASS: None if context is None else context.step_class,
        WORKFLOW_ENV_STEP_INDEX: (
            None
            if context is None or context.step_index is None
            else str(context.step_index)
        ),
        WORKFLOW_ENV_LAST_STEP_NAME: None
        if context is None
        else context.last_step_name,
        WORKFLOW_ENV_LAST_STEP_CLASS: (
            None if context is None else context.last_step_class
        ),
    }
    if operation == "run":
        updates[WORKFLOW_ENV_RUN_INPUT] = (
            None if context is None else context.input_file
        )
    elif operation == "sync":
        updates[WORKFLOW_ENV_SYNC_INPUT] = (
            None if context is None else context.input_file
        )

    previous_values = {key: os.environ.get(key) for key in updates}
    previous_presence = {key: key in os.environ for key in updates}
    try:
        for key, value in updates.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield context
    finally:
        for key in updates:
            if previous_presence[key]:
                os.environ[key] = previous_values[key]
            else:
                os.environ.pop(key, None)


def _parent_value(parent: WorkflowContext | None, field: str):
    if parent is None:
        return None
    return getattr(parent, field)


def _has_legacy_workflow_env() -> bool:
    keys = [
        WORKFLOW_ENV_INPUT_FILE,
        WORKFLOW_ENV_RUN_INPUT,
        WORKFLOW_ENV_SYNC_INPUT,
        WORKFLOW_ENV_STEP_NAME,
        WORKFLOW_ENV_STEP_CLASS,
        WORKFLOW_ENV_STEP_INDEX,
        WORKFLOW_ENV_LAST_STEP_NAME,
        WORKFLOW_ENV_LAST_STEP_CLASS,
    ]
    return any(key in os.environ for key in keys)


def _warn_legacy_env_fallback() -> None:
    global _LEGACY_ENV_FALLBACK_WARNED

    if _LEGACY_ENV_FALLBACK_WARNED:
        return

    warnings.warn(
        "Workflow state derived from legacy MYNA_* environment variables is "
        "deprecated and will be removed in Myna 2.0. Use explicit workflow "
        "context or MynaApp workflow attributes instead.",
        DeprecationWarning,
        stacklevel=3,
    )
    _LEGACY_ENV_FALLBACK_WARNED = True


def _parse_optional_int(value: str | None) -> int | None:
    if value is None:
        return None
    return int(value)
