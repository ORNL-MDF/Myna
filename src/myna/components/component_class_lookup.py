"""Functionality for looking up component subclasses"""

from .component import *
from .component_thermal import *
from .component_microstructure import *
from .component_rve import *
from .component_classify import *


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
        "thermal_part": ComponentThermalPart(),
        "thermal_region_reduced_solidification": ComponentThermalRegion(),
        "thermal_part_reduced_solidification": ComponentThermalPartReducedSolidification(),
        "thermal_region_reduced_solidification": ComponentThermalRegionReducedSolidification(),
        "thermal_part_stl": ComponentThermalPartSTL(),
        "thermal_region_stl": ComponentThermalRegionSTL(),
        "classify_thermal": ComponentClassifyThermal(),
        "classify_supervoxel": ComponentClassifySupervoxel(),
        "microstructure_part": ComponentMicrostructurePart(),
        "microstructure_region": ComponentMicrostructureRegion(),
        "rve": ComponentRVE(),
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
