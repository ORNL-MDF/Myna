"""Validate the repository documentation harness.

This check intentionally avoids external dependencies so it can run in pre-commit,
CI, and minimal local development environments.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MAX_AGENTS_LINES = 150

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
        "## Known Gaps",
    ],
    "AGENTS.md": [
        "# AGENTS.md",
        "## Start Here",
        "## Route By Task",
        "## Environment Setup",
        "## Testing Guidance",
        "## Handoff Checklist",
    ],
}

REQUIRED_AGENTS_LINKS = [
    "ARCHITECTURE.md",
    "CONTRIBUTING.md",
    "docs/developer_guide.md",
    "docs/testing.md",
    "docs/documentation.md",
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
    agents_path = REPO_ROOT / "AGENTS.md"
    agents_text = read_required_file("AGENTS.md")
    for required_link in REQUIRED_AGENTS_LINKS:
        if f"({required_link})" not in agents_text:
            fail(f"AGENTS.md must link to {required_link}")

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
            fail(f"AGENTS.md link escapes repository: {raw_target}")
        if not path.exists():
            fail(f"AGENTS.md links to missing path: {raw_target}")


def check_agents_is_compact() -> None:
    agents_text = read_required_file("AGENTS.md")
    line_count = len(agents_text.splitlines())
    if line_count > MAX_AGENTS_LINES:
        fail(
            f"AGENTS.md has {line_count} lines; keep it at or below "
            f"{MAX_AGENTS_LINES} lines and link to deeper docs for details"
        )


def main() -> None:
    check_required_headings()
    check_agents_links()
    check_agents_is_compact()
    print("docs harness check passed")


if __name__ == "__main__":
    main()
