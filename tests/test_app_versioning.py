#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import stat
import sys

import pytest

from myna.core.app.base import MynaApp


def _write_shell_executable(path, body):
    path.write_text(f"#!/bin/sh\n{body}", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def test_get_executable_version_extracts_named_regex_group(monkeypatch, tmp_path):
    exe = tmp_path / "solver"
    _write_shell_executable(
        exe,
        'printf "%s\\n" "MynaSolver version 2.3.4"\n',
    )
    monkeypatch.setattr(sys, "argv", ["test", "--exec", str(exe)])
    app = MynaApp()

    version = app.get_executable_version(
        version_args=[],
        version_regex=r"version (?P<version>\d+\.\d+\.\d+)",
    )

    assert version == "2.3.4"


def test_get_executable_version_uses_first_nonempty_line(monkeypatch, tmp_path):
    exe = tmp_path / "solver"
    _write_shell_executable(
        exe,
        'printf "%s\\n%s\\n" "" "MynaSolver 2026.05"\n',
    )
    monkeypatch.setattr(sys, "argv", ["test", "--exec", str(exe)])
    app = MynaApp()

    version = app.get_executable_version(version_args=[])

    assert version == "MynaSolver 2026.05"


def test_get_executable_version_reads_stderr_from_nonzero_command(
    monkeypatch,
    tmp_path,
):
    exe = tmp_path / "solver"
    _write_shell_executable(
        exe,
        'printf "%s\\n" "MynaSolver version 2026.05" >&2\nexit 1\n',
    )
    monkeypatch.setattr(sys, "argv", ["test", "--exec", str(exe)])
    app = MynaApp()

    version = app.get_executable_version(
        version_args=[],
        version_regex=r"version (?P<version>\S+)",
    )

    assert version == "2026.05"


def test_get_executable_version_raises_for_unmatched_pattern(monkeypatch, tmp_path):
    exe = tmp_path / "solver"
    _write_shell_executable(
        exe,
        'printf "%s\\n" "MynaSolver build unknown"\n',
    )
    monkeypatch.setattr(sys, "argv", ["test", "--exec", str(exe)])
    app = MynaApp()

    with pytest.raises(ValueError, match="Could not extract executable version"):
        app.get_executable_version(
            version_args=[],
            version_regex=r"version (?P<version>\S+)",
        )


def test_get_executable_version_honors_env_file(monkeypatch, tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    exe = bin_dir / "solver"
    _write_shell_executable(
        exe,
        'printf "%s\\n" "MynaSolver version 5.6.7"\n',
    )
    env_file = tmp_path / "solver_env.sh"
    env_file.write_text(f'PATH="{bin_dir}:$PATH"\nexport PATH\n', encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["test", "--env", str(env_file)])
    app = MynaApp()

    version = app.get_executable_version(
        default="solver",
        version_args=[],
        version_regex=r"version (?P<version>\d+\.\d+\.\d+)",
    )

    assert version == "5.6.7"
