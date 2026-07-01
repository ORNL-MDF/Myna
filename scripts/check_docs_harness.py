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
]

PR_TEMPLATE_REQUIRED_HEADINGS = [
    "## Summary",
    "## Related issues",
    "## Details",
    "## Impact",
    "## Testing strategy",
    "## Checklist",
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


def check_pr_template_guidance() -> None:
    template_text = read_required_file(".github/pull_request_template.md")
    for heading in PR_TEMPLATE_REQUIRED_HEADINGS:
        if not has_heading(template_text, heading):
            fail(
                f".github/pull_request_template.md is missing required heading: {heading}"
            )

    agents_text = read_required_file("AGENTS.md")
    required_phrases = [
        ".github/pull_request_template.md",
        "Preserve the template headings and checklist",
        "state behavior impact, risk, and testing strategy",
    ]
    for phrase in required_phrases:
        if phrase not in agents_text:
            fail(f"AGENTS.md is missing PR template guidance: {phrase}")


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


def get_comparison_base() -> str | None:
    for ref in ["origin/main", "main"]:
        merge_base = run_git_command(["merge-base", "HEAD", ref])
        if merge_base:
            return merge_base[0]
    return None


def get_changed_files() -> set[str]:
    merge_base = get_comparison_base()
    if merge_base is not None:
        changed = set(run_git_command(["diff", "--name-only", f"{merge_base}..HEAD"]))
    else:
        changed = set(run_git_command(["diff", "--name-only", "HEAD"]))
    changed.update(run_git_command(["ls-files", "--others", "--exclude-standard"]))
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
        path for path in changed_files if path_matches_any(path, ARCHITECTURE_DOC_PATHS)
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
    check_agents_is_compact()
    check_pr_template_guidance()
    check_architecture_docs_updated_for_sensitive_changes()
    print("docs harness check passed")


if __name__ == "__main__":
    main()
