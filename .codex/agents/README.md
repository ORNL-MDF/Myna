# Codex Custom Agents

This directory contains Codex custom agent definitions in the TOML format described in
the Codex subagents documentation:

- https://developers.openai.com/codex/subagents

The canonical source of truth for Myna role scope, ownership, and collaboration remains:

- `docs/agents.md`
- `docs/agents/coordinator.md`
- `docs/agents/architect.md`
- `docs/agents/integrator.md`
- `docs/agents/tester.md`
- `docs/agents/documenter.md`
- `docs/agents/reviewer.md`

## Authoring Rules

- Each `.toml` file defines one Codex custom agent.
- Agent names should stay conversational and easy to invoke in prompts.
- If a TOML file conflicts with a canonical doc, follow the canonical doc.
- Keep durable role guidance in `docs/agents/` and keep these files focused on Codex-specific configuration.

## Current Mapping

- `coordinator` -> coordination role
- `architect` -> shared core, database, and CLI workflow role
- `integrator` -> application integration role
- `tester` -> regression coverage and CI role
- `documenter` -> docs and contributor guidance role
- `reviewer` -> PR readiness, branch hygiene, and review-quality role

## Purpose

This directory gives Codex a project-scoped set of custom agents without making the
Markdown docs in `docs/agents` vendor-specific.
