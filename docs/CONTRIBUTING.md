# Contributing

Thank you for contributing to Myna.

Open a [pull request](https://help.github.com/articles/using-pull-requests/) against `main` with a clear description of your changes. When opening the pull request, complete the repository PR template to include details relevant to your change. All pull requests must pass CI checks and be approved by at least one Myna developer.

## Table of Contents

- [Contributor Workflow](#contributor-workflow)
- [Commit Message Convention](#commit-message-convention)
- [Pull Request Title Format](#pull-request-title-format)
- [Branch Naming](#branch-naming)

## Contributor Workflow

### 1. Install development dependencies

The recommended workflow uses `uv` and the checked-in `uv.lock` file. Install the
development tools from the repository root with:

```bash
uv sync --frozen --extra dev
```

If you prefer `pip`, the equivalent install is:

```bash
pip install -e .[dev]
```

### 2. Make your desired changes.

If you change dependencies locally, rerun `uv lock` and commit the updated `uv.lock`.

### 3. Run automatic commit checks with pre-commit

Use `pre-commit` to ensure local changes are ready for review.

First, install pre-commit locally:

```bash
uv tool install pre-commit --with pre-commit-uv
```

Then commit normally and allow hooks to run. You can run `pre-commit` in the repo root
directory to manually run pre-commit hooks at any time.

To skip hooks for a single commit, use `--no-verify`. You can also run checks manually using the commands below.

### 4. Run formatting and linting

Myna uses `ruff` for formatting and linting. Run these from the repository root:

```bash
uv run ruff format
uv run ruff check
```

`pylint` also runs in GitHub CI for deeper analysis. Some warnings are allowed, but CI will fail if too many new warnings reduce quality below the configured threshold.

### 5. Run unit tests

Myna uses `pytest`. Run all tests from the repository root:

```bash
uv run pytest
```

### 6. Use the portable Myna agent docs when helpful

Myna includes a portable set of development agent specifications in
[`docs/agents.md`](agents.md) and [`docs/agents/`](agents/). These documents are
tool-agnostic and can be used with Codex, Gemini, another assistant, or manually as
structured review checklists.

Use them when:

- you want a clear primary owner for a task across `core`, applications, tests, and docs
- a change crosses subsystem boundaries and needs coordination
- you want consistent done criteria for implementation, regression coverage, and docs
- you want a review pass on branch hygiene, PR readiness, security-sensitive changes, or PR text

The canonical source of truth is the Markdown documentation in `docs/agents.md`. Any
tool-specific overlays should defer to these docs rather than redefine the roles.

Codex-specific custom agents are available in `.codex/agents/` as TOML files, with
shared agent settings in `.codex/config.toml`, but they remain secondary to the
canonical Markdown docs in `docs/agents/`.

If a branch is otherwise complete but needs pull request cleanup, use the `reviewer`
agent to assess whether it is single-focus, whether commit history should be rewritten,
and whether the PR title and description match the actual change.

## Commit Message Convention

Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/):

```text
<type>(<optional scope>): <description>

<optional body>

<optional footer>
```

### Allowed Types

- `build`: Changes that affect the build system or external dependencies
- `chore`: Other changes that don't modify src or test files
- `ci`: Changes to CI configuration files and scripts
- `docs`: Documentation only changes
- `feat`: A new feature
- `fix`: A bug fix
- `perf`: A code change that improves performance
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `revert`: Reverts a previous commit
- `style`: Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc.)
- `test`: Adding missing tests or correcting existing tests

### Scope

Scope is optional, but recommended when it improves clarity.

- Use lowercase, short, subsystem-focused names.
- Prefer one scope when possible.
- Use multiple scopes only for tightly related areas.

Multi-scope format:

```text
<type>(<scope1>, <scope2>): <description>
```

Suggested scopes:

- `cli`
- `workflow`
- `metadata`
- `components`
- `files`
- `utils`
- `database`
- `additivefoam`
- `openfoam`
- `exaca`
- `thesis`
- `rve`
- `deer`
- `bnpy`
- `cubit`
- `adamantine`
- `peregrine`
- `tests`
- `docs`
- `ci`

Examples:

- `feat(cli): add dry-run flag to configure command`
- `refactor(workflow, metadata): simplify metadata loading in run pipeline`

### Subject Line

- Use imperative voice (`add`, `fix`, `update`).
- Start with a lowercase word.
- Do not end with punctuation.
- Keep it concise and specific.

Examples:

- Valid: `fix(metadata): handle missing layer-thickness field`
- Invalid: `fix(metadata): Fixed missing layer-thickness field`

### Breaking Changes

Breaking changes are considered to be anything which breaks a previous **user input** or **user interface**.
Breaking changes also include substantive change to application behavior due to internal changes (e.g.
new default values).

Use either:

1. `!` before the colon:

   ```text
   <type>(<optional scope>)!: <description>
   ```

2. A `BREAKING CHANGE:` footer:

   ```text
   <type>(<optional scope>): <description>

   <optional body>

   BREAKING CHANGE: <description of the breaking change>
   ```

## Pull Request Title Format

PR titles follow the same format and types as commit messages:

```text
<type>(<optional scope>): <description>
```

Breaking-change PR title:

```text
<type>(<optional scope>)!: <description>
```

Examples:

- `feat(cli): add support for batch exports`
- `fix(database)!: remove deprecated peregrine schema alias`

## Branch Naming

Branch names follow a similar convention to commit messages:

```text
<type>/<description>
```

### Allowed Types

Branch types are the same as commit types:

- `build`: Changes that affect the build system or external dependencies
- `chore`: Other changes that don't modify src or test files
- `ci`: Changes to CI configuration files and scripts
- `docs`: Documentation only changes
- `feat`: A new feature
- `fix`: A bug fix
- `perf`: A code change that improves performance
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `revert`: Reverts a previous commit
- `style`: Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc.)
- `test`: Adding missing tests or correcting existing tests

### Description

- Use lowercase, hyphen-separated words.
- Keep it concise and specific.
- Include issue identifiers when useful.

Examples:

- `feat/add-export-support`
- `ci/fix-pipeline`
- `fix/113-handle-missing-field`
