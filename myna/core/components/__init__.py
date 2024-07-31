"""Define the requirements and behavior of workflow components.

The myna.component module defines the base Component class and
all other modules should derive subclasses from Component.

To add a new component subclass, either add it to an existing
module if similar in functionality or create a new module if
no existing is similar to the component. For example, the
myna.components.component_microstructure module contains
subclasses for general (ComponentMicrostructure), part-based
(ComponentMicrostructurePart), and region-based
(ComponentMicrostructureRegion) microstructure simulations.

It is intended that subclasses of Component have minimal code
implementation. Largely, the subclasses should define the
following attributes of Component:

  input_requirement:
    File class from available myna.files modules.
  output_requirement:
    File class from available myna.files modules.
  data_requirements:
    List of string names for metadata requirements from available
    metadata classes corresponding to the lookup dictionary in the
    myna.metadata.data_class_lookup module.
  types:
    List of component types. The base Component class has
    ["build"], and other options are "part", "region",
    and "layer". Additional options should be appended to the
    list, because components are intended to have multiple,
    hierarchical types.
"""

from .component_class_lookup import *
from .component_solidification import *
from .component_cluster import *
from .component_microstructure import *
from .component_rve import *
from .component import *
