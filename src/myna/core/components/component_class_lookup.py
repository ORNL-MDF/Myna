#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Functionality for looking up component subclasses"""

from .component import *
from .component_solidification import *
from .component_microstructure import *
from .component_rve import *
from .component_cluster import *
from .component_mesh import *
from .component_temperature import *
from .component_melt_pool_geometry import *


def return_step_class(step_name):
    """Given a string name of a component subclass, return an instance of the subclass

    The input file for myna specifies the component class using an input string.
    This allows for a consistent interface for a Myna user to interact with
    the myna component classes. Changing the key names of the step_class_lookup
    dictionary should be avoided for backwards compatibility.

    Args:
        step_name: string of the component subclass name
    """

    step_class_lookup = {
        "general": Component(),
        "solidification_part": ComponentSolidificationPart(),
        "solidification_build_region": ComponentSolidificationBuildRegion(),
        "solidification_region": ComponentSolidificationRegion(),
        "solidification_part_solidification": ComponentSolidificationPartReduced(),
        "solidification_region_reduced": ComponentSolidificationRegionReduced(),
        "solidification_part_stl": ComponentSolidificationPartSTL(),
        "solidification_region_stl": ComponentSolidificationRegionSTL(),
        "temperature_part": ComponentTemperaturePart(),
        "temperature_final_part": ComponentTemperatureFinalPart(),
        "temperature_final_part_stl": ComponentTemperatureFinalPartSTL(),
        "cluster_solidification": ComponentClusterSolidification(),
        "cluster_supervoxel": ComponentClusterSupervoxel(),
        "microstructure_part": ComponentMicrostructurePart(),
        "microstructure_region": ComponentMicrostructureRegion(),
        "microstructure_region_slice": ComponentMicrostructureRegionSlice(),
        "rve_selection": ComponentRVE(),
        "rve_part_center": ComponentCentroidRVE(),
        "mesh_part": ComponentPartMesh(),
        "mesh_part_vtk": ComponentPartMeshVTK(),
        "melt_pool_geometry_part": ComponentMeltPoolGeometryPart(),
    }
    try:
        step_class = step_class_lookup[step_name]
    except KeyError as e:
        print(e)
        print(f'ERROR: Component name "{step_name}" is not valid. Valid step names:')
        for key in step_class_lookup.keys():
            print(f'\t- "{key}" ({step_class_lookup[key].__class__.__name__})')
        exit()
    return step_class
