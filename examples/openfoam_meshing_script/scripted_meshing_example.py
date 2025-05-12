"""Example of meshing using Myna modules from an external script.

This script provides an example of how to use the Myna application module
myna.application.openfoam to convert an STL geometry file into an
Adamantine-compatible VTK mesh.

The same functionality is available by creating a Myna input file and running
the "mesh_part_vtk" step, but this demonstrates the flexibility of developing
applications as modules within Myna in case only subsets of the
application's functionality are needed.
"""

import os
import shutil
from myna.application.openfoam import mesh

# Copy template directory
template_dir = os.path.join(
    os.environ["MYNA_APP_PATH"], "openfoam", "mesh_part_vtk", "template"
)
working_dir = os.path.abspath(os.path.join(".", "example_case"))
shutil.copytree(template_dir, working_dir, dirs_exist_ok=True)

# Get example STL location from Myna example directory (assuming this is running from
# this script's example directory)
stl_path = os.path.join("..", "Peregrine", "simulation", "meltpool", "P5", "part.stl")

# Preprocess STL and create background mesh
working_stl_path = mesh.preprocess_stl(working_dir, stl_path, convert_to_meters=0.001)
bb_dict = mesh.create_stl_cube_mesh(
    working_dir, working_stl_path, [1e-3, 1e-3, 1e-3], 1e-4
)

# Extract STL features and create part mesh
mesh.extract_stl_features(working_dir, working_stl_path, 1, bb_dict["origin"])

mesh.create_part_mesh(working_dir, working_stl_path, bb_dict)

# Slice mesh and refine layer at specified heights
mesh.slice_part_mesh(working_dir, 0.005)

mesh.refine_layer(working_dir, 0.001, 1)

# Convert mesh to Adamantine-style VTK
mesh.foam_to_adamantine(working_dir)
