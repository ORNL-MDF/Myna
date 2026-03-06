# Contributing

Thank you for contributing to Myna.

Open a [pull request](https://help.github.com/articles/using-pull-requests/) against `main` with a clear description of your changes. All pull requests must pass CI checks and be approved by at least one Myna developer.

## Table of Contents

- [Contributor Workflow](#contributor-workflow)
- [Commit Message Convention](#commit-message-convention)
- [Pull Request Title Format](#pull-request-title-format)
- [Branch Naming](#branch-naming)

## Contributor Workflow

### 1. Install development dependencies

Formatting and testing tools are included in optional development dependencies:

```bash
pip install -e .[dev]
```

### 2. Make your desired changes.

### 3. Run automatic commit checks with pre-commit

Use `pre-commit` to ensure local changes are ready for review.

1. Install it locally:

   ```bash
   pip install pre-commit
   ```

2. Enable it in this repository:

   ```bash
   pre-commit install
   ```

3. Commit normally and allow hooks to run.

To skip hooks for a single commit, use `--no-verify`. You can also run checks manually using the commands below.

### 4. Run formatting and linting

Myna uses `ruff` for formatting and linting. Run these from the repository root:

```bash
ruff format
ruff check
```

`pylint` also runs in GitHub CI for deeper analysis. Some warnings are allowed, but CI will fail if too many new warnings reduce quality below the configured threshold.

### 5. Run unit tests

Myna uses `pytest`. Run all tests from the repository root:

```bash
python -m pytest
```

## Commit Message Convention

Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/):

```text
<type>(<optional scope>): <description>

<optional body>

<optional footer>
```

### Allowed Types

- `feat`
- `fix`
- `docs`
- `style`
- `refactor`
- `perf`
- `test`
- `build`
- `ci`
- `chore`
- `revert`

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

Branch types include all commit types plus two additional types:

- `feat`
- `fix`
- `docs`
- `style`
- `refactor`
- `perf`
- `test`
- `build`
- `ci`
- `chore`
- `revert`
- `hotfix`: urgent fixes to production code
- `release`: release branches

### Description

- Use lowercase, underscore-separated words.
- Keep it concise and specific.
- Include issue identifiers when useful.

Examples:

- `feat/add_export_support`
- `hotfix/issue_413_fix_crash`
- `release/v1.2.0`
