# AGENTS.md

## Project overview

Myna is a Python package for configuring and running additive-manufacturing simulation workflows. The codebase centers on workflow orchestration, application wrappers, database readers, and the CLI used to configure and execute those workflows.

## Repository map

- `src/myna/core`: workflow logic, metadata, file types, and shared utilities
- `src/myna/application`: wrappers and templates for external simulation applications
- `src/myna/cli`: CLI entrypoints and Peregrine launcher assets
- `tests`: unit and integration tests
- `examples`: runnable workflow inputs and example datasets
- `docs`: MkDocs documentation sources

## Environment setup

- Python 3.10 or newer is required.
- Use `uv` to manage the development environment and dependencies.
- From the repository root, install the development environment with `uv sync --frozen --extra dev`.
- Use `uv run ...` for project commands.
- If dependencies change, rerun `uv lock` and commit the updated `uv.lock`.

## Development expectations

- Keep changes focused on the relevant subsystem and update tests or docs when behavior changes.
- For Python changes, run:
  - `uv run ruff format`
  - `uv run ruff check`
  - `uv run pytest`
- For documentation changes or API-surface changes that can affect docs, also run `uv run mkdocs build --strict`.
- Before handing off PR-ready work, run `uv run pre-commit run --all-files`.

## Testing notes

- The default `pytest` configuration excludes tests marked `apps`.
- Example and external-application tests require optional dependencies and executables such as 3DThesis, AdditiveFOAM, or ExaCA. Do not assume they are runnable in a normal local environment.
- If a required tool or dependency is unavailable, run the relevant subset of checks you can and clearly report what was not run.

## Git and PR conventions

- If creating a new branch, create it from `main` and use the branch naming convention from `CONTRIBUTING.md`: `<type>/<description>`.
- Use the Conventional Commit format from `CONTRIBUTING.md` for commit messages.
- Use the same Conventional Commit format for pull request titles.
- When opening a PR, complete the template in `.github/pull_request_template.md`.

## Formatting

- Always put a blank line after a heading in markdown files.
