---
title: Testing
---

# Testing

Myna uses `pytest` for unit, integration, executable, and example-case tests. Pytest
configuration lives in `pyproject.toml`.

## Default Test Suite

The default command is:

```bash
uv run pytest
```

The configured pytest addopts are:

```bash
--import-mode=importlib -m "not apps"
```

That means the default suite excludes tests marked `apps`. Use it for changes to core
workflow logic, database adapters, app wrapper helper code, file contracts, metadata,
and docs-harness Python code that does not require external simulation tools.

Use focused tests while iterating:

```bash
uv run pytest tests/test_database.py
uv run pytest tests/test_configure.py
uv run pytest tests/test_component_output_paths.py
uv run pytest tests/test_app_argument_parsing.py
```

## Markers

Markers are declared in `pyproject.toml`:

| Marker | Meaning |
| --- | --- |
| `apps` | Test requires an external application dependency |
| `examples` | Test runs a workflow case under `examples/cases/` |
| `parallel` | Test needs multiple cores to run |

External-app tests should only be reported as passing when the needed tools are
installed and available in the current environment.

## External Application Checks

Executable availability checks live in `tests/test_executables.py`:

```bash
uv run pytest -m apps tests/test_executables.py
```

These tests currently check for tools such as ExaCA, OpenFOAM/AdditiveFOAM, and
3DThesis on the current `PATH` or active environment. The Condor example test runs
when `condor` is available on `PATH` and otherwise reports an explicit skip.

Example-case tests live in `tests/test_examples.py`. They copy runnable examples to
temporary case directories under `examples/cases/`, run `myna config`, run `myna run`,
and clean up after execution.

Useful example commands:

```bash
uv run pytest -m "examples and not parallel"
uv run pytest -m "examples and parallel"
uv run pytest -m "apps and not examples"
```

The example dependency matrix is maintained in the repository file
`examples/cases/README.md`.

## CI Expectations

The main CI workflow installs with:

```bash
uv sync --locked --extra dev
```

It then runs:

```bash
uv run --frozen --no-sync pytest
uv run --frozen --no-sync python scripts/check_docs_harness.py
uv run --frozen --no-sync pylint $(git ls-files '*.py') --fail-under=7.25
uv run --frozen --no-sync scripts/group_docs.py
uv run --frozen --no-sync mkdocs build --strict
```

The external examples CI job runs in `ghcr.io/ornl-mdf/containers/ubuntu:dev`,
installs all extras, checks external executables, and runs example tests in serial and
parallel marker groups.
