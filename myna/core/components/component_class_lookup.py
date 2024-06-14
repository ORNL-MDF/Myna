"""Functionality for looking up component subclasses"""

from .component import *
from .component_solidification import *
from .component_microstructure import *
from .component_rve import *
from .component_classify import *
from .component_mesh import *
from .component_temperature import *


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
        "solidification_region_reduced": ComponentSolidificationRegion(),
        "solidification_part_solidification": ComponentSolidificationPartReduced(),
        "solidification_region_reduced": ComponentSolidificationRegionReduced(),
        "solidification_part_stl": ComponentSolidificationPartSTL(),
        "solidification_region_stl": ComponentSolidificationRegionSTL(),
        "temperature_part": ComponentTemperaturePart(),
        "classify_solidification": ComponentClassifySolidification(),
        "classify_supervoxel": ComponentClassifySupervoxel(),
        "microstructure_part": ComponentMicrostructurePart(),
        "microstructure_region": ComponentMicrostructureRegion(),
        "rve": ComponentRVE(),
        "mesh_part": ComponentPartMesh(),
        "mesh_part_vtk": ComponentPartMeshVTK(),
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
