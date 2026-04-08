# Updating the Changelog

`CHANGELOG.md` records notable project changes. Update it for any pull request that introduces behavior, features, fixes, or changes that users, developers, or downstream integrations should be able to discover later.

Myna follows:

- [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
- [The Good Docs Project - Changelog Template](https://www.thegooddocsproject.dev/template/changelog)

---

## Where to edit

- Edit [`CHANGELOG.md`](https://github.com/ORNL-MDF/Myna/blob/main/CHANGELOG.md) at the repository root.
- Add all new changes under `## Unreleased`.
- Keep releases in reverse chronological order (newest first).
- Separate releases with `---`.

---

## Versioning

Use `MAJOR.MINOR.PATCH - YYYY-MM-DD` (e.g., `1.2.0 - 2026-03-12`) in the header to describe the release:

- MAJOR: version when you add substantial capability and/or dependency changes
- MINOR: version when you add incremental functionality
- PATCH: version when you make backward compatible bug fixes

The release versioning will correspond to the package version in `pyproject.toml`.

Unreleased changes will correspond to the package version of the next MINOR release (e.g., `1.2.0-dev0` is the development package version following `1.1.0` release).

---

## Change types

Use only relevant sections:

- `Added`
- `Changed`
- `Deprecated`
- `Removed`
- `Fixed`
- `Security`
- `Breaking changes`

Omit empty sections.

---

## Writing guidelines

- Start each bullet with a verb (`Added`, `Changed`, `Fixed`, etc.).
- Focus on user-visible outcomes, not implementation details.
- Do not include placeholder text (e.g., `None.`).

---

## Workflow

1. Add changes under `## Unreleased` as PRs merge.
2. When releasing:

   - Rename `## Unreleased` → `## MAJOR.MINOR.PATCH - YYYY-MM-DD`
   - Add `### Release highlights` (2–5 bullets summarizing key changes)
   - Insert a new empty `## Unreleased` section at the top

---

## Canonical structure

Use a single structure for both **Unreleased** and **released versions**:

```markdown
## <VERSION OR "Unreleased">
<!--
- Use "Unreleased" with no date
- Use "MAJOR.MINOR.PATCH - YYYY-MM-DD" for releases
- Omit empty sections
-->

### Release highlights
<!--
Only include for released versions.
Summarize the most important new features, enhancements, fixes, or breaking changes that were introduced in this release.
-->

- Added ...
- Changed ...

### Added
<!-- Describe new features added since the last release and why they matter. -->

- Added ...

### Changed
<!-- Describe updates to existing functionality, such as improved behavior, performance, or error handling. -->

- Changed ...

### Deprecated
<!-- List features being phased out, explain why, and point readers to the recommended alternative. -->

- Deprecated ...

### Removed
<!-- List features, commands, APIs, or behaviors that were removed in this release. -->

- Removed ...

### Fixed
<!--
Describe bugs fixed in this release and how the fixes improve the user experience.
Link to the PR or issue that fixed the bug, if applicable.
-->

- Fixed ...

### Security
<!-- List any resolved common vulnerabilities and exposures (CVEs) or other security improvements. -->

- Improved security around ...

### Breaking changes
<!-- Describe incompatible changes and any upgrade steps users need to take. -->

- Changed ...
```

### Key differences

- **Unreleased**

  - Title: `## Unreleased`
  - No date
  - No `Release highlights`

- **Released versions**

  - Title includes version and date
  - Must include `### Release highlights`
