#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import sys

import pytest

from myna.core.app.base import MynaApp


def test_validate_executable_can_be_strict(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["test"])
    app = MynaApp()

    with pytest.raises(FileNotFoundError, match="executable"):
        app.validate_executable(
            ["definitely-not-installed-myna-executable"], strict=True
        )


def test_validate_all_executable_false_disables_strict_default(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["test"])
    app = MynaApp()
    app.settings = {"myna": {"validate_all_executable": False}}

    with pytest.warns(UserWarning, match="executable"):
        app.validate_executable(["definitely-not-installed-myna-executable"])
