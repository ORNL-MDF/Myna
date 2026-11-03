#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Tests for package imports that should not load unrelated backends."""

import subprocess
import sys


def _run_import_check(source):
    result = subprocess.run(
        [sys.executable, "-c", source],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_import_myna_is_lightweight():
    _run_import_check(
        """
import sys
import myna
assert 'myna.core' not in sys.modules
assert 'myna.application' not in sys.modules
assert 'myna.database' not in sys.modules
"""
    )


def test_import_core_does_not_load_application_backends():
    _run_import_check(
        """
import sys
import myna.core
assert 'myna.application' not in sys.modules
assert 'myna.database.pelican' not in sys.modules
assert 'myna.database.nist_ambench_2022' not in sys.modules
"""
    )


def test_import_database_does_not_load_all_adapters():
    _run_import_check(
        """
import sys
import myna.database
assert 'myna.database.myna_json' not in sys.modules
assert 'myna.database.pelican' not in sys.modules
assert 'myna.database.peregrine' not in sys.modules
assert 'myna.database.peregrine_hdf5' not in sys.modules
assert 'myna.database.nist_ambench_2022' not in sys.modules
"""
    )


def test_database_lookup_loads_only_selected_adapter():
    _run_import_check(
        """
import sys
import myna.database

database = myna.database.return_datatype_class('none')
assert database.__class__.__name__ == 'NoDatabase'
assert 'myna.database.myna_json' not in sys.modules
assert 'myna.database.pelican' not in sys.modules
assert 'myna.database.peregrine' not in sys.modules
assert 'myna.database.peregrine_hdf5' not in sys.modules
assert 'myna.database.nist_ambench_2022' not in sys.modules
"""
    )


def test_accessing_adapter_reports_its_missing_dependency_late():
    _run_import_check(
        """
import builtins
import myna.database

real_import = builtins.__import__

def blocked_import(name, *args, **kwargs):
    if name == 'h5py' or name.startswith('h5py.'):
        raise ModuleNotFoundError('blocked for import isolation test', name='h5py')
    return real_import(name, *args, **kwargs)

builtins.__import__ = blocked_import
try:
    myna.database.PeregrineHDF5
except ModuleNotFoundError as error:
    assert error.name == 'h5py'
else:
    raise AssertionError('PeregrineHDF5 should import h5py only when accessed')
"""
    )
