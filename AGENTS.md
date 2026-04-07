# AGENTS.md

This file gives coding agents the minimum project context needed to work effectively
in Myna. Keep this file practical and execution-focused. For portable role-based
ownership and cross-functional coordination, use the canonical agent docs in
[`docs/agents.md`](docs/agents.md) and [`docs/agents/`](docs/agents/).

## Project Overview

Myna is a Python framework for additive-manufacturing workflows built around three
main areas:

- `src/myna/core/`: shared workflow semantics, components, files, metadata, and CLI flow
- `src/myna/application/`: application-specific adapters and execution wiring
- `src/myna/database/`: database readers and related integration logic

Most code changes should preserve existing workflow abstractions instead of adding
one-off behavior for a single application or example.

## Environment and Dependency Setup

Prefer `uv` for environment management, dependency installation, and command execution.
This repository already includes a [`uv.lock`](uv.lock) file, and CI uses `uv`, so agents
should follow the same path unless the user explicitly asks for something else.

From the repository root:

```bash
uv sync --locked --all-extras --dev
```

Use `uv run` for Python commands instead of activating environments manually:

```bash
uv run pytest
uv run ruff format
uv run ruff check
uv run pylint $(git ls-files '*.py') --fail-under=7.25
```

When dependencies are already synced and you only need to execute a command, prefer:

```bash
uv run --frozen --no-sync <command>
```

Use `pip` only when the user specifically asks for it or when `uv` is unavailable.

## Working Norms

- Read the nearest relevant docs before changing behavior that affects workflows, CLI,
  contributor process, or app integrations.
- Keep changes narrow and consistent with existing abstractions.
- Do not create new workflow semantics in app-specific code when they belong in `core`.
- Do not silently change user-visible paths, config precedence, or execution semantics
  without updating tests and docs.
- Treat local uncommitted changes as user-owned unless you created them.

## Testing Instructions

Always choose the smallest test set that meaningfully covers the change, then scale up
only if needed.

Common commands from the repository root:

```bash
uv run --frozen --no-sync pytest
uv run --frozen --no-sync pytest tests/test_component_output_paths.py
uv run --frozen --no-sync pytest -k "<pattern>"
uv run --frozen --no-sync pytest -m "not apps"
uv run --frozen --no-sync pytest -m "apps and not examples"
uv run --frozen --no-sync pytest -n 4 -vv -m "examples and not parallel"
uv run --frozen --no-sync pytest -n 2 -vv -m "examples and parallel"
```

Important pytest markers defined by the project:

- `apps`: requires external application dependencies
- `examples`: runs example cases
- `parallel`: needs multiple cores

Testing expectations:

- Add or update tests for behavior changes unless there is a clear reason not to.
- Prefer focused unit or workflow tests before slow example coverage.
- If a change touches shared behavior, do not rely only on manual reasoning.
- If local validation is incomplete because external applications are unavailable, say
  exactly what still needs CI or an app-enabled environment.

## Linting and Verification

Before finishing substantial code changes, run the relevant checks you touched:

```bash
uv run --frozen --no-sync ruff format
uv run --frozen --no-sync ruff check
uv run --frozen --no-sync pylint $(git ls-files '*.py') --fail-under=7.25
```

If docs or generated API docs may be affected, also run:

```bash
uv run --frozen --no-sync scripts/group_docs.py
uv run --frozen --no-sync mkdocs build --strict
```

## Docs and Coordination

Use [`docs/agents.md`](docs/agents.md) to route work to the right primary role:

- `core`, `database`, `cli`: `architect`
- `application`: `integrator`
- `tests`, CI, pre-commit: `tester`
- `docs`: `documenter`
- PR readiness, branch hygiene, and reviewability: `reviewer` as a supporting advisor

Bring in coordination when a task crosses boundaries, especially for:

- shared workflow semantics that affect application adapters
- CLI, config, environment, or path-layout behavior
- test strategy decisions across unit, example, and app-marked coverage
- contributor workflow or review-policy changes

Use `reviewer` before opening or merging a pull request when you want help checking:

- whether the branch is a single coherent change
- whether commit history should be squashed, reordered, or renamed
- whether the diff contains obvious security issues such as secrets or local paths
- whether the PR title and description clearly match the branch contents

## External Dependency Notes

Some Myna functionality depends on external non-Python applications such as 3DThesis,
AdditiveFOAM, and ExaCA. Do not assume those tools are available locally.

- Avoid broad example or app-marked runs when a focused non-app test is sufficient.
- When external executables are required, prefer targeted checks and clearly report any
  environment assumptions.
- Do not rewrite tests to hide legitimate external dependency requirements; instead,
  document what was or was not validated locally.

## Change Hygiene

- Keep documentation in sync with behavior changes.
- Do not edit CI, pre-commit, or contributor workflow casually; these changes affect
  every contributor.
- Prefer explicit failure messages, targeted tests, and small diffs.
- If instructions here conflict with a direct user request, follow the user request.
