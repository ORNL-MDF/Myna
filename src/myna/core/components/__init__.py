#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
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

from .component_class_lookup import return_step_class
from .component_cluster import (
    ComponentCluster,
    ComponentClusterSolidification,
    ComponentClusterSupervoxel,
)
from .component_creep import (
    ComponentCreepTimeSeries,
    ComponentCreepTimeSeriesPart,
    ComponentCreepTimeSeriesRegion,
)
from .component_melt_pool_geometry import (
    ComponentMeltPoolGeometry,
    ComponentMeltPoolGeometryPart,
)
from .component_mesh import (
    ComponentMesh,
    ComponentPartMesh,
    ComponentPartMeshVTK,
    ComponentVTKToExodusMeshPart,
    ComponentVTKToExodusMeshRegion,
)
from .component_microstructure import (
    ComponentMicrostructure,
    ComponentMicrostructurePart,
    ComponentMicrostructureRegion,
    ComponentMicrostructureRegionSlice,
)
from .component_rve import ComponentRVE, ComponentCentroidRVE
from .component_solidification import (
    ComponentSolidification,
    ComponentSolidificationPart,
    ComponentSolidificationRegion,
    ComponentSolidificationBuildRegion,
    ComponentSolidificationPartSTL,
    ComponentSolidificationRegionSTL,
    ComponentSolidificationPartReduced,
    ComponentSolidificationRegionReduced,
    ComponentSolidificationRegionReducedSTL,
)
from .component_temperature import (
    ComponentTemperature,
    ComponentTemperaturePart,
    ComponentTemperaturePartPVD,
)
from .component import Component

__all__ = [
    "return_step_class",
    "ComponentCluster",
    "ComponentClusterSolidification",
    "ComponentClusterSupervoxel",
    "ComponentCreepTimeSeries",
    "ComponentCreepTimeSeriesPart",
    "ComponentCreepTimeSeriesRegion",
    "ComponentMeltPoolGeometry",
    "ComponentMeltPoolGeometryPart",
    "ComponentMesh",
    "ComponentPartMesh",
    "ComponentPartMeshVTK",
    "ComponentVTKToExodusMeshPart",
    "ComponentVTKToExodusMeshRegion",
    "ComponentMicrostructure",
    "ComponentMicrostructurePart",
    "ComponentMicrostructureRegion",
    "ComponentMicrostructureRegionSlice",
    "ComponentRVE",
    "ComponentCentroidRVE",
    "ComponentSolidification",
    "ComponentSolidificationPart",
    "ComponentSolidificationRegion",
    "ComponentSolidificationBuildRegion",
    "ComponentSolidificationPartSTL",
    "ComponentSolidificationRegionSTL",
    "ComponentSolidificationPartReduced",
    "ComponentSolidificationRegionReduced",
    "ComponentSolidificationRegionReducedSTL",
    "ComponentTemperature",
    "ComponentTemperaturePart",
    "ComponentTemperaturePartPVD",
    "Component",
]
