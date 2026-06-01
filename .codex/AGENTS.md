# AGENTS.md

## Project Overview

Myna is a Python package for additive-manufacturing simulation workflows. It connects
build database readers, workflow components, application wrappers, metadata, file
contracts, examples, and CLI stages for configuring, running, and syncing simulations.

Agents usually work on workflow orchestration, database adapters, application wrappers,
example cases, tests, and documentation. Do not change product behavior for docs-only
tasks.

## Start Here

- Read [ARCHITECTURE.md](../ARCHITECTURE.md) for system structure, control flow, and
  dependency boundaries.
- Read [CONTRIBUTING.md](../CONTRIBUTING.md) for branch, commit, PR title, and PR template
  conventions.
- Read [docs/developer_guide.md](../docs/developer_guide.md) before adding components,
  metadata, file types, or application wrappers.
- Read [docs/testing.md](../docs/testing.md) for markers, external-app tests, and CI
  expectations.
- Read [docs/documentation.md](../docs/documentation.md) before changing docs or the agent
  harness.
- Inspect nearby code and tests before changing a subsystem.

## Repository Map

| Path | Purpose |
| --- | --- |
| `src/myna/core/` | Generic workflow orchestration, components, metadata, files, app helpers, and utilities |
| `src/myna/core/workflow/` | `myna config`, `myna run`, `myna sync`, `myna status`, input loading, and Peregrine launch flow |
| `src/myna/core/components/` | Component classes and user-facing component lookup keys |
| `src/myna/core/files/` | Output file contracts and validation/sync value extraction |
| `src/myna/core/metadata/` | Metadata requirement classes and lookup keys |
| `src/myna/database/` | Database readers/adapters for Peregrine, HDF5, MynaJSON, Pelican, AMBench, and no-database mode |
| `src/myna/application/` | External application wrappers, stage scripts, and templates |
| `src/myna/cli/peregrine_launcher/` | Peregrine-oriented launch templates and default workspace |
| `tests/` | Pytest suite; default config excludes `apps` tests |
| `examples/cases/` | Runnable workflow cases and per-case dependency matrix |
| `examples/databases/` | Sample database fixtures for examples/tests |
| `examples/workspaces/` | Example workspace YAML settings |
| `examples/utils/` | Standalone Python API examples |
| `docs/` | MkDocs source pages |
| `scripts/` | Maintenance scripts, including docs generation and harness validation |
| `.github/workflows/` | CI, pre-commit, and docs deployment workflows |

See [ARCHITECTURE.md](../ARCHITECTURE.md) for the full repository map.

## Environment Setup

Start with the development tool preflight:

```bash
python3 scripts/check_dev_tools.py
```

On a fresh clone, install the development environment with `uv` from the repository
root:

```bash
uv sync --frozen --extra dev
python3 scripts/check_dev_tools.py
```

If an agent shell has read-only home caches, use writable cache directories before
running `uv` or `pre-commit`:

```bash
export UV_CACHE_DIR=/tmp/uv-cache
export PRE_COMMIT_HOME=/tmp/pre-commit-cache
```

Install optional Python extras only when needed:

```bash
uv sync --frozen --extra exaca
uv sync --frozen --extra bnpy
uv sync --frozen --extra cubit
uv sync --frozen --extra deer
```

If dependency declarations change, run `uv lock` and commit the updated `uv.lock`.

## Common Commands

| Task | Command |
| --- | --- |
| Check dev tools | `python3 scripts/check_dev_tools.py` |
| Format | `uv run ruff format` |
| Lint | `uv run ruff check` |
| Run default tests | `uv run pytest` |
| Run focused test | `uv run pytest tests/test_database.py` |
| Check external executables | `uv run pytest -m apps tests/test_executables.py` |
| Generate API docs | `uv run scripts/group_docs.py` |
| Build docs | `uv run mkdocs build --strict` |
| Check docs harness | `uv run python scripts/check_docs_harness.py` |
| Run pre-commit | `uv run pre-commit run --all-files` |

## Testing Guidance

Before handoff, run the most relevant focused tests plus formatting/linting for code
changes. For docs-only changes, run the docs harness and docs build when dependencies
are available.

Default pytest excludes tests marked `apps`. Tests marked `apps`, `examples`, or
`parallel` may require external tools such as 3DThesis, AdditiveFOAM/OpenFOAM, ExaCA,
Adamantine, Cubit, or DEER. Do not claim those checks passed unless the local tools
were available and the commands actually ran.

When a command cannot run because of missing optional dependencies, missing external
executables, container restrictions, or network access, report the exact command and
the reason.

## Architecture Rules

- Keep generic orchestration in `src/myna/core/`, especially under
  `src/myna/core/workflow/`.
- Keep external-tool behavior, templates, executable handling, and postprocessing in
  `src/myna/application/`.
- Keep database-specific parsing and sync behavior in `src/myna/database/`.
- Keep components declarative: define requirements, output contracts, and hierarchy
  without embedding one application's execution details.
- Preserve user-facing lookup keys in component, metadata, and database lookup modules
  unless a breaking change is intentional and documented.
- Parse and validate external files at subsystem boundaries.
- Do not import test helpers from runtime modules.
- Keep generated outputs and machine-local paths out of source control.

## Documentation Rules

- Update `ARCHITECTURE.md` when changing subsystem boundaries, control flow, public
  extension points, or major dependencies.
- Update user/developer docs when changing commands, examples, installation, optional
  dependencies, or public behavior.
- Add a decision record under `docs/decisions/` for decisions that are not obvious from
  code review alone.
- Keep this file short; link to deeper docs instead of expanding it.
- Run `uv run python scripts/check_docs_harness.py` after changing `.codex/AGENTS.md`,
  `ARCHITECTURE.md`, or linked docs.

## PR and Commit Guidance

Contributions target `main` and must pass CI with at least one Myna developer approval.
Use Conventional Commits for commits and PR titles:

```text
<type>(<optional scope>): <description>
```

Branch names use:

```text
<type>/<description>
```

Examples: `docs/agent-harness`, `fix/database-paths`, `feat(cli): add dry-run flag`.
Complete `.github/pull_request_template.md` and state behavior impact, risk, and
testing strategy.

## Security and Data Handling

- Do not commit secrets, credentials, private data, or machine-specific executable
  paths.
- Do not commit large generated simulation outputs, local logs, `site/`,
  `docs/api-docs/`, or case output folders unless they are intentional fixtures.
- Avoid destructive commands against user data and example fixtures.
- Treat `examples/databases/` as fixture data; keep generated registered/simulation
  outputs ignored unless maintainers explicitly request otherwise.

## Handoff Checklist

- Relevant tests, lint, docs, or harness checks run.
- Commands not run are listed with concrete reasons.
- Files changed are summarized.
- Public behavior changes, compatibility risks, or known gaps are called out.
- Docs and examples are updated when commands, inputs, outputs, or extension points
  change.
- If code changes touch `src/myna/core/workflow/`, `src/myna/core/components/`,
  `src/myna/core/app/`, `src/myna/core/context.py`, `src/myna/database/`, CLI behavior,
  app extension patterns, or subsystem boundaries, update `ARCHITECTURE.md` and
  relevant developer docs, or state why no docs update was needed.
