from .component_general import *
from .component_thermal import *
from .component_thermal_region import *

def return_step_class(step_name):
    step_class_lookup = {
        "general": ComponentGeneral(),
        "thermal": ComponentThermal(),
        "thermal_region": ComponentThermalRegion()
    }
    try:
        step_class = step_class_lookup[step_name]
    except KeyError as e:
        print(e)
        print("ERROR: Component name is not valid. Valid step names:")
        for key in step_class_lookup.keys():
            print(f"\t- {key}: {step_class_lookup[key]}")
        exit()
    return step_class