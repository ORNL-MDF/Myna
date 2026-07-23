#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import os
import shutil
from pathlib import PureWindowsPath

import myna
import yaml

from myna.core.workflow.load_input import (
    _shares_path_anchor,
    load_input,
    write_input,
)
from myna.core.workflow.run import run


def test_shares_path_anchor_rejects_cross_drive_windows_paths():
    assert _shares_path_anchor(
        PureWindowsPath("C:/bundle/workspace.yaml"),
        PureWindowsPath("C:/bundle"),
    )
    assert not _shares_path_anchor(
        PureWindowsPath("D:/bundle/workspace.yaml"),
        PureWindowsPath("C:/bundle"),
    )


def test_write_input_relativizes_runtime_paths_only(tmp_path):
    bundle_dir = tmp_path / "bundle"
    workspace_file = bundle_dir / "workspace.yaml"
    output_file = bundle_dir / "myna_output" / "P1" / "0" / "demo" / "output.csv"
    scanpath_file = bundle_dir / "myna_resources" / "P1" / "0" / "scanpath.txt"

    workspace_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    scanpath_file.parent.mkdir(parents=True, exist_ok=True)
    workspace_file.write_text("fake_app: {}\n", encoding="utf-8")
    scanpath_file.write_text("x\ty\n0\t0\n", encoding="utf-8")

    input_file = bundle_dir / "input.yaml"
    settings = {
        "steps": [],
        "data": {
            "build": {
                "path": "/source/build",
                "parts": {
                    "P1": {
                        "layer_data": {
                            "0": {
                                "scanpath": {
                                    "file_local": str(scanpath_file),
                                    "file_database": "/source/db/P1/0000000.txt",
                                }
                            }
                        }
                    }
                },
            },
            "output_paths": {"demo": [str(output_file)]},
        },
        "myna": {"workspace": str(workspace_file)},
    }

    write_input(settings, input_file, relative_paths=True)
    raw_settings = yaml.safe_load(input_file.read_text(encoding="utf-8"))

    assert raw_settings["data"]["build"]["path"] == "/source/build"
    assert raw_settings["myna"]["workspace"] == "workspace.yaml"
    assert raw_settings["data"]["output_paths"]["demo"] == [
        os.path.join("myna_output", "P1", "0", "demo", "output.csv")
    ]
    assert raw_settings["data"]["build"]["parts"]["P1"]["layer_data"]["0"]["scanpath"][
        "file_local"
    ] == os.path.join("myna_resources", "P1", "0", "scanpath.txt")
    assert (
        raw_settings["data"]["build"]["parts"]["P1"]["layer_data"]["0"]["scanpath"][
            "file_database"
        ]
        == "/source/db/P1/0000000.txt"
    )

    loaded_settings = load_input(input_file)
    assert loaded_settings["data"]["build"]["path"] == "/source/build"
    assert loaded_settings["myna"]["workspace"] == str(workspace_file.resolve())
    assert loaded_settings["data"]["output_paths"]["demo"] == [
        str(output_file.resolve())
    ]
    assert loaded_settings["data"]["build"]["parts"]["P1"]["layer_data"]["0"][
        "scanpath"
    ]["file_local"] == str(scanpath_file.resolve())
    assert (
        loaded_settings["data"]["build"]["parts"]["P1"]["layer_data"]["0"]["scanpath"][
            "file_database"
        ]
        == "/source/db/P1/0000000.txt"
    )


def test_write_input_only_relativizes_data_file_local_paths(tmp_path):
    bundle_dir = tmp_path / "bundle"
    workspace_file = bundle_dir / "workspace.yaml"
    scanpath_file = bundle_dir / "myna_resources" / "P1" / "0" / "scanpath.txt"
    myna_file_local = bundle_dir / "myna_flags" / "workspace_flag.txt"
    step_file_local = bundle_dir / "step_flags" / "configure_flag.txt"

    workspace_file.parent.mkdir(parents=True, exist_ok=True)
    scanpath_file.parent.mkdir(parents=True, exist_ok=True)
    myna_file_local.parent.mkdir(parents=True, exist_ok=True)
    step_file_local.parent.mkdir(parents=True, exist_ok=True)
    workspace_file.write_text("fake_app: {}\n", encoding="utf-8")
    scanpath_file.write_text("x\ty\n0\t0\n", encoding="utf-8")
    myna_file_local.write_text("workspace\n", encoding="utf-8")
    step_file_local.write_text("configure\n", encoding="utf-8")

    input_file = bundle_dir / "input.yaml"
    write_input(
        {
            "steps": [
                {
                    "demo": {
                        "class": "fake_component",
                        "application": "fake_app",
                        "configure": {"file_local": str(step_file_local)},
                    }
                }
            ],
            "data": {
                "build": {
                    "path": "/source/build",
                    "parts": {
                        "P1": {
                            "layer_data": {
                                "0": {"scanpath": {"file_local": str(scanpath_file)}}
                            }
                        }
                    },
                }
            },
            "myna": {
                "workspace": str(workspace_file),
                "file_local": str(myna_file_local),
            },
        },
        input_file,
        relative_paths=True,
    )

    raw_settings = yaml.safe_load(input_file.read_text(encoding="utf-8"))
    assert raw_settings["data"]["build"]["parts"]["P1"]["layer_data"]["0"]["scanpath"][
        "file_local"
    ] == os.path.join("myna_resources", "P1", "0", "scanpath.txt")
    assert raw_settings["myna"]["file_local"] == str(myna_file_local)
    assert raw_settings["steps"][0]["demo"]["configure"]["file_local"] == str(
        step_file_local
    )


def test_load_input_only_resolves_data_file_local_paths(tmp_path):
    bundle_dir = tmp_path / "bundle"
    workspace_file = bundle_dir / "workspace.yaml"
    scanpath_file = bundle_dir / "myna_resources" / "P1" / "0" / "scanpath.txt"

    workspace_file.parent.mkdir(parents=True, exist_ok=True)
    scanpath_file.parent.mkdir(parents=True, exist_ok=True)
    workspace_file.write_text("fake_app: {}\n", encoding="utf-8")
    scanpath_file.write_text("x\ty\n0\t0\n", encoding="utf-8")

    input_file = bundle_dir / "input.yaml"
    input_file.write_text(
        yaml.safe_dump(
            {
                "steps": [
                    {
                        "demo": {
                            "class": "fake_component",
                            "application": "fake_app",
                            "configure": {
                                "file_local": "step_flags/configure_flag.txt"
                            },
                        }
                    }
                ],
                "data": {
                    "build": {
                        "path": "/source/build",
                        "parts": {
                            "P1": {
                                "layer_data": {
                                    "0": {
                                        "scanpath": {
                                            "file_local": os.path.join(
                                                "myna_resources",
                                                "P1",
                                                "0",
                                                "scanpath.txt",
                                            )
                                        }
                                    }
                                }
                            }
                        },
                    }
                },
                "myna": {
                    "workspace": str(workspace_file),
                    "file_local": "myna_flags/workspace_flag.txt",
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    loaded_settings = load_input(input_file)
    assert loaded_settings["data"]["build"]["parts"]["P1"]["layer_data"]["0"][
        "scanpath"
    ]["file_local"] == str(scanpath_file.resolve())
    assert loaded_settings["myna"]["file_local"] == "myna_flags/workspace_flag.txt"
    assert loaded_settings["steps"][0]["demo"]["configure"]["file_local"] == (
        "step_flags/configure_flag.txt"
    )


def test_load_input_expands_layer_range_strings(tmp_path):
    input_file = tmp_path / "input.yaml"
    input_file.write_text(
        yaml.safe_dump(
            {
                "steps": [],
                "data": {
                    "build": {
                        "parts": {
                            "P1": {
                                "layers": "1-3, 5",
                                "regions": {"core": {"layers": ["7-8", 10]}},
                            }
                        },
                        "build_regions": {"BR1": {"layerlist": "[11-12, 14]"}},
                    }
                },
                "myna": {},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    loaded_settings = load_input(input_file)

    assert loaded_settings["data"]["build"]["parts"]["P1"]["layers"] == [1, 2, 3, 5]
    assert loaded_settings["data"]["build"]["parts"]["P1"]["regions"]["core"][
        "layers"
    ] == [7, 8, 10]
    assert loaded_settings["data"]["build"]["build_regions"]["BR1"]["layerlist"] == [
        11,
        12,
        14,
    ]


def test_write_input_anchors_case_file_local_paths_to_case_directory(tmp_path):
    bundle_dir = tmp_path / "bundle"
    case_dir = bundle_dir / "myna_output" / "P1" / "0" / "demo"
    scanpath_file = bundle_dir / "myna_resources" / "P1" / "0" / "scanpath.txt"

    case_dir.mkdir(parents=True, exist_ok=True)
    scanpath_file.parent.mkdir(parents=True, exist_ok=True)
    scanpath_file.write_text("x\ty\n0\t0\n", encoding="utf-8")

    case_file = case_dir / "myna_data.yaml"
    case_settings = {
        "build": {
            "path": "/source/build",
            "parts": {
                "P1": {
                    "layer_data": {
                        "0": {
                            "scanpath": {
                                "file_local": str(scanpath_file),
                                "file_database": "/source/db/P1/0000000.txt",
                            }
                        }
                    }
                }
            },
        },
        "myna": {},
    }

    write_input(case_settings, case_file, relative_paths=True)
    raw_settings = yaml.safe_load(case_file.read_text(encoding="utf-8"))
    file_local = raw_settings["build"]["parts"]["P1"]["layer_data"]["0"]["scanpath"][
        "file_local"
    ]

    assert not os.path.isabs(file_local)
    assert (case_dir / file_local).resolve() == scanpath_file.resolve()
    assert (
        raw_settings["build"]["parts"]["P1"]["layer_data"]["0"]["scanpath"][
            "file_database"
        ]
        == "/source/db/P1/0000000.txt"
    )

    loaded_settings = load_input(case_file)
    assert loaded_settings["build"]["parts"]["P1"]["layer_data"]["0"]["scanpath"][
        "file_local"
    ] == str(scanpath_file.resolve())


def test_run_resolves_relative_paths_after_moving_bundle(tmp_path, monkeypatch):
    source_bundle = tmp_path / "source_bundle"
    workspace_file = source_bundle / "workspace.yaml"
    scanpath_file = source_bundle / "myna_resources" / "P1" / "0" / "scanpath.txt"
    case_dir = source_bundle / "myna_output" / "P1" / "0" / "demo"
    input_file = source_bundle / "input.yaml"

    workspace_file.parent.mkdir(parents=True, exist_ok=True)
    scanpath_file.parent.mkdir(parents=True, exist_ok=True)
    case_dir.mkdir(parents=True, exist_ok=True)
    workspace_file.write_text("fake_app: {}\n", encoding="utf-8")
    scanpath_file.write_text("x\ty\n0\t0\n", encoding="utf-8")

    write_input(
        {
            "build": {
                "path": "/source/build",
                "parts": {
                    "P1": {
                        "layers": [0],
                        "layer_data": {
                            "0": {
                                "scanpath": {
                                    "file_local": str(scanpath_file),
                                    "file_database": "/source/db/P1/0000000.txt",
                                }
                            }
                        },
                    }
                },
            },
            "myna": {},
        },
        case_dir / "myna_data.yaml",
        relative_paths=True,
    )
    write_input(
        {
            "steps": [{"demo": {"class": "fake_component", "application": "fake_app"}}],
            "data": {
                "build": {
                    "name": "myna_output",
                    "path": "/source/build",
                    "parts": {"P1": {"layers": [0]}},
                },
                "output_paths": {"demo": [str(case_dir / "output.csv")]},
            },
            "myna": {"workspace": str(workspace_file)},
        },
        input_file,
        relative_paths=True,
    )

    moved_bundle = tmp_path / "moved_bundle"
    shutil.move(str(source_bundle), str(moved_bundle))

    captured = {}

    class FakeComponent:
        def __init__(self):
            self.name = None
            self.data = {}
            self.myna = {}

        def apply_settings(self, step_settings, data_settings, myna_settings):
            self.data = data_settings
            self.myna = myna_settings

        def run_component(self):
            output_path = self.data["output_paths"][self.name][0]
            case_settings = load_input(
                os.path.join(os.path.dirname(output_path), "myna_data.yaml")
            )
            scanpath = case_settings["build"]["parts"]["P1"]["layer_data"]["0"][
                "scanpath"
            ]
            captured["output_path"] = output_path
            captured["workspace"] = self.myna["workspace"]
            captured["build_path"] = case_settings["build"]["path"]
            captured["file_local"] = scanpath["file_local"]
            captured["file_database"] = scanpath["file_database"]

    monkeypatch.setattr(
        myna.core.components,
        "return_step_class",
        lambda *args, **kwargs: FakeComponent(),
    )

    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        run(os.fspath(moved_bundle / "input.yaml"))
    finally:
        os.chdir(cwd)

    assert captured["output_path"] == str(
        (moved_bundle / "myna_output" / "P1" / "0" / "demo" / "output.csv").resolve()
    )
    assert captured["workspace"] == str((moved_bundle / "workspace.yaml").resolve())
    assert captured["build_path"] == "/source/build"
    assert captured["file_local"] == str(
        (moved_bundle / "myna_resources" / "P1" / "0" / "scanpath.txt").resolve()
    )
    assert captured["file_database"] == "/source/db/P1/0000000.txt"
