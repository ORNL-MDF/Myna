# Myna Development Agents

Myna uses a small set of portable development agent roles to keep work specialized
without losing architectural consistency. These roles are defined in plain Markdown
so they can be used with Codex, Gemini, another assistant, or manually by a
contributor coordinating their own work.

The canonical agent specs are:

- [`coordinator`](agents/coordinator.md)
- [`architect`](agents/architect.md)
- [`integrator`](agents/integrator.md)
- [`tester`](agents/tester.md)
- [`documenter`](agents/documenter.md)
- [`reviewer`](agents/reviewer.md)

Optional Codex-specific custom agents live in `.codex/agents/` as TOML files, with
shared Codex agent settings in `.codex/config.toml`. Those Codex-specific files are
convenience overlays only and must defer to the canonical specs listed here.

Current canonical naming:

- `coordinator`: coordinates cross-cutting work
- `architect`: owns shared core, database, and CLI workflow behavior
- `integrator`: owns application adapter behavior
- `tester`: owns regression coverage, CI, and contributor quality gates
- `documenter`: owns docs, onboarding, and contributor-facing guidance
- `reviewer`: owns pull request readiness, commit hygiene, and change-level review quality

## Goals

- Keep Myna-specific development context reusable across tools
- Route work to the right specialist for the subsystem being changed
- Require coordination when a task crosses core workflow, applications, tests, or docs
- Preserve maintainability by preventing app-local fixes from redefining shared behavior

## Agent Routing

Use exactly one primary agent for implementation ownership, then involve supporting
agents when the task crosses boundaries. Supporting agents review impact in their
area; they do not replace the primary owner.

| Work area | Primary agent |
| --- | --- |
| `src/myna/core/**`, `src/myna/database/**`, `src/myna/cli/**` | `architect` |
| `src/myna/application/**` | `integrator` |
| `tests/**`, `.github/workflows/**`, `.pre-commit-config.yaml` | `tester` |
| `docs/**`, `README.md` | `documenter` |

Use `coordinator` when:

- a change spans more than one primary work area
- a change affects workflow semantics, CLI behavior, path layout, or environment handling
- a change modifies both implementation and contributor-facing process
- it is unclear whether behavior belongs in shared `core` code or app-specific code

If a task is limited to one work area and does not change shared policy, the primary
agent may proceed without `coordinator` involvement.

Use `reviewer` when:

- checking whether a branch is ready to open or merge as a pull request
- reviewing whether the branch is a single-focus change or should be split
- cleaning up messy commit history before review
- looking for obvious security review issues such as hard-coded secrets or local paths
- drafting pull request text from the actual branch contents

`reviewer` is a supporting advisory role, not a replacement for the primary subsystem
owner. It does not own implementation paths.

## Collaboration Rules

### `coordinator` review is mandatory for:

- changes affecting both `core` and any application adapter
- changes to workflow file layout, output path behavior, or configuration precedence
- changes to CLI inputs, environment variables, or cross-step execution semantics
- changes that require test strategy decisions across unit, example, and app-marked tests

### Required supporting reviews

- Include `tester` for any code change, even if only to confirm existing coverage is sufficient.
- Include `documenter` when a change affects user inputs, outputs, setup, contributor workflow,
  or expected review process.
- Include `reviewer` when preparing a branch for PR review, merge, or history cleanup.
- Include `architect` when an application change introduces reusable workflow semantics.
- Include `integrator` when shared changes may alter template use,
  executable invocation, or app-level configure/execute/postprocess behavior.

## Definition of Done

A task is done when all of the following are true:

- the primary agent's owned subsystem is updated coherently
- cross-cutting impact has been reviewed by the required supporting agents
- tests are either added, updated, or explicitly deemed unnecessary with a clear reason
- user-facing or contributor-facing documentation is updated when behavior changed
- the result fits existing Myna abstractions instead of introducing one-off workflow rules
- if `reviewer` was involved, the branch history and PR framing are reviewable and aligned
  with contributor guidance

## Portability Rules

These agent specs are intentionally tool-agnostic:

- Agent instructions must refer to Myna paths, behaviors, interfaces, and review criteria.
- Canonical specs must not depend on Codex-only or vendor-specific features.
- Outputs should be described in plain language, such as proposing regression tests or
  reviewing path ownership.
- Any future tool-specific overlay must defer to these documents and must not redefine roles.
- If portability adds duplication or brittle maintenance, the canonical Markdown docs win.

## Manual Workflow

Contributors can use these roles without any special runtime:

1. Read this page to choose the primary agent for the task.
2. Copy the relevant agent spec into your coding assistant as the task frame.
3. If the task crosses boundaries, also provide the `coordinator` spec and any required
   supporting agent specs.
4. Compare the resulting work against the definition of done on this page before merging.
5. If you are preparing a pull request, use the `reviewer` spec to check branch scope,
   history quality, security-sensitive changes, and PR wording before requesting review.

This same workflow should work with Codex, Gemini, or a human contributor using the
agent docs as structured review checklists.

## Example Routing

- A change to `src/myna/core/components/component.py` that affects output path safety:
  `architect` primary, `tester` required, `coordinator` if the change affects app behavior or docs expectations.
- A fix to application MPI flags or template execution wiring:
  `integrator` primary, `tester` required, `architect` if shared execution semantics change.
- A contributor process update:
  `documenter` primary, `coordinator` only if the change alters engineering policy across code review, testing, and branching.
- A CI or pre-commit change:
  `tester` primary, `documenter` if contributor instructions must change.
- A branch that is functionally ready but has questionable commit structure or needs PR text:
  keep the original primary owner, then involve `reviewer` before opening the pull request.
