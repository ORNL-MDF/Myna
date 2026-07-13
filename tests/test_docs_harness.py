#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "check_docs_harness.py"
SPEC = importlib.util.spec_from_file_location("test_docs_harness_module", MODULE_PATH)
DOCS_HARNESS = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(DOCS_HARNESS)


def test_get_changed_files_uses_merge_base_diff_and_untracked(monkeypatch):
    def fake_run_git_command(args):
        command_map = {
            ("merge-base", "HEAD", "origin/main"): ["abc123"],
            ("diff", "--name-only", "abc123..HEAD"): ["src/myna/core/context.py"],
            ("ls-files", "--others", "--exclude-standard"): ["scratch.txt"],
        }
        return command_map.get(tuple(args), [])

    monkeypatch.setattr(DOCS_HARNESS, "run_git_command", fake_run_git_command)

    assert DOCS_HARNESS.get_changed_files() == {
        "src/myna/core/context.py",
        "scratch.txt",
    }


def test_get_changed_files_falls_back_to_dirty_worktree(monkeypatch):
    def fake_run_git_command(args):
        command_map = {
            ("merge-base", "HEAD", "origin/main"): [],
            ("merge-base", "HEAD", "main"): [],
            ("diff", "--name-only", "HEAD"): ["scripts/check_docs_harness.py"],
            ("ls-files", "--others", "--exclude-standard"): [],
        }
        return command_map.get(tuple(args), [])

    monkeypatch.setattr(DOCS_HARNESS, "run_git_command", fake_run_git_command)

    assert DOCS_HARNESS.get_changed_files() == {"scripts/check_docs_harness.py"}


def test_architecture_docs_required_for_sensitive_branch_changes(monkeypatch, capsys):
    monkeypatch.setattr(
        DOCS_HARNESS,
        "get_changed_files",
        lambda: {"src/myna/core/context.py"},
    )

    with pytest.raises(SystemExit):
        DOCS_HARNESS.check_architecture_docs_updated_for_sensitive_changes()
    assert "architecture-sensitive files changed" in capsys.readouterr().err


def test_architecture_docs_check_passes_when_docs_are_updated(monkeypatch):
    monkeypatch.setattr(
        DOCS_HARNESS,
        "get_changed_files",
        lambda: {"src/myna/core/context.py", "ARCHITECTURE.md"},
    )

    DOCS_HARNESS.check_architecture_docs_updated_for_sensitive_changes()
