import pytest
from importlib.metadata import version

import myna


# This test is primarily intended to ensure the test suite itself is working.
def test_version():
    assert version("myna") == "0.1.0.dev"
