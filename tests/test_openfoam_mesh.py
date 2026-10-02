#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Tests for OpenFOAM command dispatch."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from myna.application.openfoam import mesh


def _app(*, docker_image=None):
    app = Mock()
    app.args = SimpleNamespace(docker_image=docker_image)
    process = Mock(stdout=None)
    app.start_subprocess.return_value = process
    app.start_subprocess_with_mpi_args.return_value = process
    return app, process


def test_run_command_serial_preserves_subprocess_kwargs():
    app, process = _app()
    environment = {"FOAM_VERBOSE": "1"}

    mesh.run_command(["checkMesh"], app=app, parallel=False, env=environment)

    app.start_subprocess.assert_called_once_with(["checkMesh"], env=environment)
    app.start_subprocess_with_mpi_args.assert_not_called()
    app.wait_for_process_success.assert_called_once_with(process)


def test_run_command_parallel_uses_mpi_and_preserves_kwargs():
    app, process = _app()
    output = Mock()
    process.stdout = output
    process.communicate.return_value = (b"mesh output", b"")

    result = mesh.run_command(
        ["snappyHexMesh"], app=app, parallel=True, stdout=output, stderr=output
    )

    assert result == b"mesh output"
    app.start_subprocess_with_mpi_args.assert_called_once_with(
        ["snappyHexMesh"], stdout=output, stderr=output
    )
    app.start_subprocess.assert_not_called()


def test_run_command_docker_maps_current_case_without_dropping_kwargs(
    tmp_path, monkeypatch
):
    app, process = _app(docker_image="openfoam:test")
    monkeypatch.chdir(tmp_path)
    environment = {"FOAM_VERBOSE": "1"}

    mesh.run_command(["foamToVTK"], app=app, env=environment)

    kwargs = app.start_subprocess.call_args.kwargs
    assert kwargs["env"] == environment
    assert kwargs["remove"] is True
    assert kwargs["working_dir"] == "/home/myna"
    assert kwargs["volumes"][str(tmp_path)] == {"bind": "/home/myna"}


def test_run_command_propagates_app_process_failure():
    app, process = _app()
    failure = RuntimeError("process failed")
    app.wait_for_process_success.side_effect = failure

    with pytest.raises(RuntimeError, match="process failed"):
        mesh.run_command(["checkMesh"], app=app)
