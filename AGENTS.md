# AGENTS.md

## Project Overview

Myna is a Python package for additive-manufacturing simulation workflows. It connects
build database readers, workflow components, application wrappers, metadata, file
contracts, examples, and CLI stages for configuring, running, and syncing simulations.

Agents usually work on workflow orchestration, database adapters, application wrappers,
example cases, tests, and documentation. Do not change product behavior for docs-only
tasks.

## Start Here

- Read [ARCHITECTURE.md](ARCHITECTURE.md) for the system map, control flow, extension
  points, and dependency boundaries.
- Read [CONTRIBUTING.md](CONTRIBUTING.md) for branch, commit, PR title, and PR template
  conventions.
- Inspect nearby code and tests before changing a subsystem.

## Route By Task

| Task | Start with |
| --- | --- |
| Workflow orchestration, component routing, database adapters, app wrappers, metadata, or file contracts | [ARCHITECTURE.md](ARCHITECTURE.md) and nearby code/tests |
| Adding components, metadata, file types, database readers, or application wrappers | [docs/developer_guide.md](docs/developer_guide.md) |
| Tests, markers, external-app checks, or CI validation | [docs/testing.md](docs/testing.md) |
| Documentation, generated API docs, MkDocs navigation, or this harness | [docs/documentation.md](docs/documentation.md) |
| Contributor workflow, branch names, commits, PR titles, or PR template expectations | [CONTRIBUTING.md](CONTRIBUTING.md) |

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

If the preflight reports PATH or cache problems, follow its suggested fix before
running `uv`, `pytest`, or `pre-commit`. Install optional Python extras only when a
task needs them. If dependency declarations change, run `uv lock` and commit the
updated `uv.lock`.

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
the reason. Do not replace a missing external-app test with a default pytest run and
call the external behavior covered. Say what was covered and what remains unverified.

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
- Include details in your change summary following the [PR template](.github/pull_request_template.md)
  for decisions that are not obvious from code review alone, such as change intent or broader
  architectural decisions that may not be readily apparent.
- Keep this file short; link to deeper docs instead of expanding it.
- Run `uv run python scripts/check_docs_harness.py` after changing `AGENTS.md`,
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
- Commands not run are listed with concrete reasons, such as missing external executable, unavailable
  optional extra, container dependency, or network restriction.
- Files changed are summarized.
- Public behavior changes, compatibility risks, or known gaps are called out.
- Docs and examples are updated when commands, inputs, outputs, or extension points
  change.
