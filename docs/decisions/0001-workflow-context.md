---
title: Workflow Context
---

# 0001: Use Explicit Workflow Context for App Stage Execution

## Status

Accepted

## Context

Myna workflows pass ordered step information from `myna run` and `myna sync` into
components, application wrappers, metadata helpers, and database sync code. Previously,
some of this state was communicated through mutable `MYNA_*` environment variables and
app-stage Python subprocesses. That made workflow state implicit and worked against the
object-oriented structure used by components and `MynaApp` subclasses.

Application stage files such as `configure.py`, `execute.py`, and `postprocess.py` are
still useful extension points and are commonly implemented with `argparse`.

## Decision

Workflow run and sync state is carried by `myna.core.context.WorkflowContext`.
`Component.run_component()` imports available app-stage modules and calls their stage
function, or `main()`, in-process. During each stage call, Myna temporarily populates
`sys.argv` with the configured stage arguments so existing `argparse`-based wrappers
continue to behave as command-line stages.

`MynaApp` reads explicit context first and falls back to legacy `MYNA_*` environment
variables for direct script invocation compatibility. New code should use
`WorkflowContext`, `MynaApp` attributes, or `get_workflow_input_file()` rather than
direct `os.environ` reads for workflow state.

## Consequences

Workflow state is explicit in normal orchestration, easier to test, and no longer
requires environment-variable mutation between app-stage subprocesses. Existing stage
modules remain compatible if they expose the expected callable and parse arguments with
`argparse`.

Direct invocation of app-stage scripts can still rely on legacy environment-variable
fallbacks, but that path is compatibility behavior rather than the preferred extension
pattern.

## Validation

- `uv run pytest`
- `tests/test_workflow_context.py`
