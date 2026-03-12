#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
from pathlib import Path

import pytest

from myna.core.components.component import Component
from myna.core.files.file import File


class DummyOutputFile(File):
    """Minimal output file type for path validation tests."""

    def __init__(self, file):
        super().__init__(file)
        self.filetype = ".csv"

    def file_is_valid(self):
        return True


@pytest.fixture
def component(tmp_path, monkeypatch):
    input_file = tmp_path / "input.yaml"
    input_file.write_text("steps: []\n", encoding="utf-8")
    monkeypatch.setenv("MYNA_INPUT", str(input_file))

    component = Component()
    component.name = "demo-step"
    component.data = {"build": {"name": "build-1"}}
    component.output_requirement = DummyOutputFile
    return component


def test_get_files_from_template_allows_relative_subdirectories(component, tmp_path):
    files = component.get_files_from_template("results/output.csv")

    assert files == [
        str((tmp_path / "build-1" / "demo-step" / "results" / "output.csv").resolve())
    ]


def test_get_output_files_rejects_traversal(component):
    component.output_template = "../../secret.csv"

    with pytest.raises(
        ValueError, match="Configured template path escapes the workflow case directory"
    ):
        component.get_output_files()


def test_get_files_from_template_rejects_absolute_paths(component):
    with pytest.raises(
        ValueError,
        match="Configured template path must be relative to the workflow case directory",
    ):
        component.get_files_from_template(str(Path("/tmp/secret.csv")))
