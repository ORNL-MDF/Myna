"""Validate the repository documentation harness.

This check intentionally avoids external dependencies so it can run in pre-commit,
CI, and minimal local development environments.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_HEADINGS = {
    "ARCHITECTURE.md": [
        "# Architecture",
        "## Status",
        "## System Purpose",
        "## Architectural Goals",
        "## Repository Map",
        "## Runtime and Packaging Model",
        "## Main Concepts and Domain Model",
        "## Control Flow",
        "## Dependency Boundaries",
        "## Extension Points",
        "## Testing and Validation Architecture",
        "## Documentation Architecture",
        "## External Systems and Data",
        "## Known Gaps and Follow-Up Work",
    ],
    ".codex/AGENTS.md": [
        "# AGENTS.md",
        "## Project Overview",
        "## Start Here",
        "## Repository Map",
        "## Environment Setup",
        "## Common Commands",
        "## Testing Guidance",
        "## Architecture Rules",
        "## Documentation Rules",
        "## PR and Commit Guidance",
        "## Security and Data Handling",
        "## Handoff Checklist",
    ],
}

ARCHITECTURE_SENSITIVE_PATHS = [
    "src/myna/core/workflow/",
    "src/myna/core/components/",
    "src/myna/core/app/",
    "src/myna/core/context.py",
    "src/myna/database/",
    "src/myna/application/readme.md",
]

ARCHITECTURE_DOC_PATHS = [
    "ARCHITECTURE.md",
    "docs/developer_guide.md",
    "docs/decisions/",
]


def fail(message: str) -> None:
    print(f"docs harness check failed: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_required_file(relative_path: str) -> str:
    path = REPO_ROOT / relative_path
    if not path.exists():
        fail(f"missing required file: {relative_path}")
    return path.read_text(encoding="utf-8")


def has_heading(text: str, heading: str) -> bool:
    pattern = rf"^{re.escape(heading)}\s*$"
    return re.search(pattern, text, flags=re.MULTILINE) is not None


def check_required_headings() -> None:
    for relative_path, headings in REQUIRED_HEADINGS.items():
        text = read_required_file(relative_path)
        for heading in headings:
            if not has_heading(text, heading):
                fail(f"{relative_path} is missing required heading: {heading}")


def iter_markdown_links(text: str) -> list[str]:
    return re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)


def is_external_link(target: str) -> bool:
    return target.startswith(("http://", "https://", "mailto:", "#"))


def check_agents_links() -> None:
    agents_path = REPO_ROOT / ".codex" / "AGENTS.md"
    agents_text = read_required_file(".codex/AGENTS.md")
    if "(../ARCHITECTURE.md)" not in agents_text:
        fail(".codex/AGENTS.md must link to ../ARCHITECTURE.md")

    for raw_target in iter_markdown_links(agents_text):
        target = raw_target.strip()
        if is_external_link(target):
            continue
        target = target.split("#", 1)[0].strip()
        if not target:
            continue
        if target.startswith("<") and target.endswith(">"):
            target = target[1:-1]
        path = (agents_path.parent / target).resolve(strict=False)
        try:
            path.relative_to(REPO_ROOT)
        except ValueError:
            fail(f".codex/AGENTS.md link escapes repository: {raw_target}")
        if not path.exists():
            fail(f".codex/AGENTS.md links to missing path: {raw_target}")


def run_git_command(args: list[str]) -> list[str]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return []

    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def get_changed_files() -> set[str]:
    changed = set(run_git_command(["diff", "--name-only", "HEAD"]))
    changed.update(
        run_git_command(["ls-files", "--others", "--exclude-standard"])
    )
    return changed


def path_matches_any(path: str, prefixes_or_paths: list[str]) -> bool:
    return any(
        path == candidate.rstrip("/") or path.startswith(candidate)
        for candidate in prefixes_or_paths
    )


def check_architecture_docs_updated_for_sensitive_changes() -> None:
    changed_files = get_changed_files()
    if not changed_files:
        return

    sensitive_changes = sorted(
        path
        for path in changed_files
        if path_matches_any(path, ARCHITECTURE_SENSITIVE_PATHS)
    )
    if not sensitive_changes:
        return

    docs_changes = sorted(
        path
        for path in changed_files
        if path_matches_any(path, ARCHITECTURE_DOC_PATHS)
    )
    if docs_changes:
        return

    changed_list = "\n".join(f"  - {path}" for path in sensitive_changes)
    required_list = "\n".join(f"  - {path}" for path in ARCHITECTURE_DOC_PATHS)
    fail(
        "architecture-sensitive files changed without architecture documentation "
        "updates.\nChanged files:\n"
        f"{changed_list}\nUpdate at least one of:\n{required_list}\n"
        "If no docs update is needed, state that explicitly in the PR."
    )


def main() -> None:
    check_required_headings()
    check_agents_links()
    check_architecture_docs_updated_for_sensitive_changes()
    print("docs harness check passed")


if __name__ == "__main__":
    main()
