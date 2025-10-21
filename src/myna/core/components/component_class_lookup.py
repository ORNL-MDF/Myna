#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Functionality for looking up component subclasses"""

import myna.core.components as comp


def return_step_class(step_name, verbose=True):
    """Given a string name of a component subclass, return an instance of the subclass

    The input file for myna specifies the component class using an input string.
    This allows for a consistent interface for a Myna user to interact with
    the myna component classes. Changing the key names of the step_class_lookup
    dictionary should be avoided for backwards compatibility.

    Args:
        step_name: string of the component subclass name
    """

    step_class_lookup = {
        "general": comp.Component(),
        "solidification_part": comp.ComponentSolidificationPart(),
        "solidification_build_region": comp.ComponentSolidificationBuildRegion(),
        "solidification_region": comp.ComponentSolidificationRegion(),
        "solidification_part_solidification": comp.ComponentSolidificationPartReduced(),
        "solidification_region_reduced": comp.ComponentSolidificationRegionReduced(),
        "solidification_region_reduced_stl": comp.ComponentSolidificationRegionReducedSTL(),
        "solidification_part_stl": comp.ComponentSolidificationPartSTL(),
        "solidification_region_stl": comp.ComponentSolidificationRegionSTL(),
        "temperature_part": comp.ComponentTemperaturePart(),
        "temperature_part_pvd": comp.ComponentTemperaturePartPVD(),
        "cluster_solidification": comp.ComponentClusterSolidification(),
        "cluster_supervoxel": comp.ComponentClusterSupervoxel(),
        "microstructure_part": comp.ComponentMicrostructurePart(),
        "microstructure_region": comp.ComponentMicrostructureRegion(),
        "microstructure_region_slice": comp.ComponentMicrostructureRegionSlice(),
        "rve_selection": comp.ComponentRVE(),
        "rve_part_center": comp.ComponentCentroidRVE(),
        "mesh_part": comp.ComponentPartMesh(),
        "mesh_part_vtk": comp.ComponentPartMeshVTK(),
        "melt_pool_geometry_part": comp.ComponentMeltPoolGeometryPart(),
        "vtk_to_exodus_part": comp.ComponentVTKToExodusMeshPart(),
        "vtk_to_exodus_region": comp.ComponentVTKToExodusMeshRegion(),
        "creep_timeseries": comp.ComponentCreepTimeSeries(),
        "creep_timeseries_part": comp.ComponentCreepTimeSeriesPart(),
        "creep_timeseries_region": comp.ComponentCreepTimeSeriesRegion(),
        "single_track_calibration": comp.Component(),
    }
    try:
        step_class = step_class_lookup[step_name]
    except KeyError as e:
        if verbose:
            print(e)
            print(
                f'ERROR: Component name "{step_name}" is not valid. Valid step names:'
            )
            for key, obj in step_class_lookup.items():
                print(f'\t- "{key}" ({obj.__class__.__name__})')
        raise KeyError(e) from e
    return step_class
