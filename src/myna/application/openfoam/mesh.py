#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Functions to create and manipulate OpenFOAM meshes"""
import os
import re
import subprocess
import vtk
import numpy as np
from myna.core.utils import working_directory


def update_parameter(foamdict_file, entry, value):
    """Updates the given parameter in an OpenFOAM dictionary

    Args:
        foamdict_file: (str) path to the OpenFOAM dictionary file
        entry: (str) key for the entry, e.g., "geometry/refinementBox/min"
        value: (str or numeric) value to write. If the value contains spaces it must be
            enclosed in doublequotes, e.g., `value='"test string"'`!
    """

    os.system(f"foamDictionary -entry {entry} -set '{value}' {foamdict_file}")


def preprocess_stl(case_dir, stl_path, convert_to_meters=1):
    """Preprocesses an STL for meshing:

    1. creates a copy of the stl file
    2. converts stl to meters
    3. cleans the copied stl file to the template directory
    """
    stl_file_name = os.path.basename(stl_path)

    # copy the stl to constant/triSurface for openfoam functions
    working_stl_dir = os.path.join(case_dir, "constant", "triSurface")
    working_stl_path = os.path.join(working_stl_dir, stl_file_name)

    os.system(f"mkdir -p {working_stl_dir}")
    os.system(f"cp -rf {stl_path} {working_stl_path}")

    # scale the stl file to meters
    scaling = " ".join(str(convert_to_meters) for _ in range(3))
    os.system(
        f'surfaceTransformPoints "scale=({scaling})" {working_stl_path} {working_stl_path}'
    )

    # generic surface clean (removes ambiguous patches in stl file)
    os.system(f"surfaceClean {working_stl_path} {working_stl_path} 0 0")

    return working_stl_path


def extract_stl_features(case_dir, stl_path, refinement_level, origin):
    """extract features from the stl file and set parameters in files"""

    stl_file_name = os.path.basename(stl_path)

    # extract the surface features from the stl file
    surface_features_dict = f"{case_dir}/system/surfaceFeaturesDict"
    update_parameter(surface_features_dict, "surfaces", f'( "{stl_file_name}" )')
    os.system(f"surfaceFeatures -case {case_dir}")
    emesh_name = stl_file_name.split(".")[0] + ".eMesh"

    # update entries is snappyHexMeshDict
    snappyhexmesh_dict = f"{case_dir}/system/snappyHexMeshDict"
    origin = " ".join(list(map(str, origin)))
    print("origin for stl features: ", origin)

    update_parameter(snappyhexmesh_dict, "geometry/part/file", f'"{stl_file_name}"')
    update_parameter(
        snappyhexmesh_dict,
        "castellatedMeshControls/features",
        f'( {"{"} file "{emesh_name}"; level {refinement_level}; {"}"} )',
    )
    update_parameter(
        snappyhexmesh_dict, "castellatedMeshControls/locationInMesh", f"( {origin} )"
    )
    update_parameter(
        snappyhexmesh_dict,
        "castellatedMeshControls/refinementSurfaces/part/level",
        f"( {refinement_level} {refinement_level} )",
    )
    update_parameter(
        snappyhexmesh_dict,
        "castellatedMeshControls/refinementRegions/part/levels",
        f"( ( {refinement_level} {refinement_level} ) )",
    )


def construct_bounding_box_dict(rve, rve_pad):
    """Construct a dictionary to define the bounding box properties

    Args:
        rve: (np.array(3,2))
    """
    bb_min = [rve[0][0] - rve_pad[0], rve[0][1] - rve_pad[1], rve[0][2] - rve_pad[2]]
    bb_max = [rve[1][0] + rve_pad[0], rve[1][1] + rve_pad[1], rve[1][2]]
    span = [b - a for (a, b) in zip(bb_min, bb_max)]
    origin = [a + b / 2.0 for (a, b) in zip(bb_min, span)]
    return {
        "bb_min": bb_min,
        "bb_max": bb_max,
        "bb": bb_min + bb_max,
        "span": span,
        "origin": origin,
    }


def construct_mesh_bounding_box_dict(case_dir, tolerance=1e-8):
    """Construct a dictionary to define the bounding box properties based on the mesh
    of an existing OpenFOAM case

    Args:
        case_dir: (str) path to case directory
        tolerance: (float) tolerance used to pad the edge of the bounding box
    """
    s = subprocess.check_output(
        f"checkMesh -case {case_dir} -noTopology | grep -i 'Overall domain bounding box'",
        shell=True,
    ).decode("utf-8")

    bb_str = re.findall(r"\(([^)]+)", s)
    tolerance = 1e-8
    rve = np.array(
        [float(x) for x in bb_str[0].split(" ")],
        [float(x) for x in bb_str[1].split(" ")],
    )
    rve_pad = np.array([tolerance, tolerance, tolerance])
    bb_dict = construct_bounding_box_dict(rve, rve_pad)
    return bb_dict


def calc_n_cells(bb_dict, spacing):
    """Calculates the number of cells needed to span the bounding box

    Args:
        bb_dict: (dict) bounding box dictionary as defined by
            `construct_bounding_box_dict()`
        spacing: (float) mesh spacing, in meters
    """
    return np.array([round(a / b) for (a, b) in zip(bb_dict["span"], spacing)])


def create_cube_mesh(case_dir, spacing, rve, rve_pad):
    """Create a cube mesh at the specified rve location

    Args:
        case_dir: (str) path to case directory
        spacing: (float) mesh spacing for cube mesh
        rve: (np.array(3,2)) cube bounds ((xmin, ymin, zmin, (xmax, ymax, zmax)))
        rve_pad: (np.array(3,)) padding to add to rve bounds (xpad, ypad, zpad)
    """

    # get the bounding box of the stl to create block mesh
    bb_dict = construct_bounding_box_dict(rve, rve_pad)
    n_cells = calc_n_cells(bb_dict, spacing)

    # update blockMeshDict file in the case directory
    block_mesh_dict = os.path.join(case_dir, "system/blockMeshDict")
    keys = ["xmin", "ymin", "zmin", "xmax", "ymax", "zmax"]
    for k, key in enumerate(keys):
        update_parameter(block_mesh_dict, key, bb_dict["bb"][k])
    keys = ["nx", "ny", "nz"]
    for k, key in enumerate(keys):
        update_parameter(block_mesh_dict, key, n_cells[k])

    os.system(f"blockMesh -case {case_dir}")

    return bb_dict


def create_stl_cube_mesh(case_dir, working_stl_path, spacing, tolerance):
    """create a background mesh using blockMesh around the stl file"""

    # get the bounding box of the stl to create background mesh
    s = subprocess.check_output(
        f"surfaceCheck {working_stl_path} | grep -i 'Bounding Box :'", shell=True
    ).decode("utf-8")
    bb_str = re.findall(r"\(([^)]+)", s)
    rve = np.array(
        [
            [float(x) for x in bb_str[0].split(" ")],
            [float(x) for x in bb_str[1].split(" ")],
        ]
    )
    rve_pad = np.array([tolerance, tolerance, tolerance])
    bb_dict = create_cube_mesh(case_dir, spacing, rve, rve_pad)

    return bb_dict


def create_part_mesh(case_dir, stl_path, bb_dict, mpi_args=None):
    """create the part mesh"""

    if mpi_args is None:
        os.system(f"snappyHexMesh -case {case_dir} -overwrite")
    else:
        start = mpi_args.find("-np ") + len("-np ")

        if start == -1:
            start = mpi_args.find("-n ") + len("-n ")

        end = mpi_args.find(" ", start)

        if end == -1:
            end = len(mpi_args)

        nprocs = mpi_args[start:end]

        # Decompose the case for meshing
        update_parameter(
            f"{case_dir}/system/decomposeParDict", "numberOfSubdomains", nprocs
        )
        os.system(f"decomposePar -case {case_dir} -force")

        # Mesh and reconstruct the case, then remove decomposed files
        os.system(f"{mpi_args} snappyHexMesh -case {case_dir} -parallel -overwrite")
        os.system(f"reconstructParMesh -case {case_dir} -withZero -constant")
        os.system(f"rm -rf {case_dir}/processor*")

    # move bottom of mesh to z=0 plane
    translation = " ".join(str(t) for t in [0, 0, -bb_dict["bb_min"][2]])
    os.system(f'transformPoints -case {case_dir} "translate=({translation})"')

    # save a copy of polyMesh for the part in the working directory
    stl_file_name = os.path.basename(stl_path)
    polymesh_copy = f"{case_dir}/{stl_file_name.split('.')[0]}.polyMesh"
    os.system(f"cp -rf {case_dir}/constant/polyMesh {polymesh_copy}")


def foam_to_adamantine(case_dir, precision=8):
    """convert OpenFOAM VTK format to adamantine VTK format"""

    # Create OpenFOAM VTK file
    os.system(f"foamToVTK -case {case_dir} -constant -ascii")
    vtk_file_path = os.path.join(case_dir, "VTK", os.path.basename(case_dir) + "_0.vtk")

    # Read the OpenFOAM VTK file
    reader = vtk.vtkUnstructuredGridReader()  # pylint: disable=no-member
    reader.SetFileName(vtk_file_path)
    reader.Update()
    grid = reader.GetOutput()

    # Write the Adamantine VTK file
    with open(vtk_file_path, "w", encoding="utf-8") as f:
        f.write("# vtk DataFile Version 3.0\n")
        f.write("****\n")
        f.write("ASCII\n")
        f.write("DATASET UNSTRUCTURED_GRID\n")

        # Write points
        f.write(f"POINTS {grid.GetNumberOfPoints()} float\n")
        for i in range(grid.GetNumberOfPoints()):
            point = grid.GetPoint(i)
            f.write(
                f"{point[0]:.{precision}f} {point[1]:.{precision}f} {point[2]:.{precision}f}\n"
            )

        # Write cells
        f.write(
            f"CELLS {grid.GetNumberOfCells()} {grid.GetCells().GetData().GetNumberOfTuples()}\n"
        )
        id_list = vtk.vtkIdList()  # pylint: disable=no-member
        for i in range(grid.GetNumberOfCells()):
            grid.GetCellPoints(i, id_list)
            f.write(
                f"{id_list.GetNumberOfIds()} "
                + " ".join(
                    [str(id_list.GetId(j)) for j in range(id_list.GetNumberOfIds())]
                )
                + "\n"
            )

        # Write cell types
        f.write(f"CELL_TYPES {grid.GetNumberOfCells()}\n")
        for i in range(grid.GetNumberOfCells()):
            f.write(f"{grid.GetCellType(i)}\n")

    return vtk_file_path


def slice_part_mesh(case_dir, height):
    """slice the part mesh at a specified build height"""

    # Get the bounding box of the existing mesh
    bb_dict = construct_mesh_bounding_box_dict(case_dir)
    bb_dict["bb"][-1] = height

    # Update topoSetDict parameters
    toposetdict = f"{case_dir}/system/topoSetDict"
    keys = ["xmin", "ymin", "zmin", "xmax", "ymax", "zmax"]
    for k, key in enumerate(keys):
        update_parameter(toposetdict, key, bb_dict["bb"][k])

    # Remove the created cellSet and renumber new mesh
    os.system(f"topoSet -case {case_dir}")
    os.system(f"subsetMesh -case {case_dir} -overwrite c0 -patch part")
    os.system(f"rm -rf {case_dir}/constant/polyMesh/sets")
    os.system(f"rm -rf {case_dir}/constant/polyMesh/*Level")
    os.system(f"renumberMesh -case {case_dir} -overwrite")

    # Align the sliced mesh with the top at z=0 plane
    s = subprocess.check_output(
        f'checkMesh -case {case_dir} -noTopology | grep -i "Overall domain bounding box"',
        shell=True,
    ).decode("utf-8")
    zmax = float(re.findall(r"\(([^)]+)", s)[-1].split(" ")[-1])
    translation = " ".join(list(map(str, [0, 0, -zmax])))
    os.system(f'transformPoints -case {case_dir} "translate=({translation})"')


def refine_mesh_in_box(case_dir, bb):
    """Refine the mesh for an OpenFOAM case within a bounding box using the
    case's `system/refineMeshDict` settings.

    Args:
        case_dir: (str) path to case directory
        bb: (np.array, shape (2,3)) bounding box ((xmin, ymin, zmin),(xmax, ymax, zmax))
    """

    center = [
        0.5 * (bb[0][0] + bb[1][0]),
        0.5 * (bb[0][1] + bb[1][1]),
        0.5 * (bb[0][2] + bb[1][2]),
    ]

    refine_mesh_dict = f"{case_dir}/system/refineMeshDict"
    update_parameter(
        refine_mesh_dict,
        "geometry/refinementBox/min",
        f"( {bb[0][0]} {bb[0][1]} {bb[0][2]} )",
    )
    update_parameter(
        refine_mesh_dict,
        "geometry/refinementBox/max",
        f"( {bb[1][0]} {bb[1][1]} {bb[1][2]} )",
    )
    update_parameter(
        refine_mesh_dict,
        "castellatedMeshControls/locationInMesh",
        f"( {center[0]} {center[1]} {center[2]} )",
    )

    with working_directory(case_dir):
        os.system("snappyHexMesh -dict system/refineMeshDict -overwrite")


def refine_layer(case_dir, refinement_depth, refinement_level):
    """Refine the mesh for an OpenFOAM case for a region near the max-z surface

    Args:
        case_dir: (str) path to case directory
        refinement_depth: (float) depth of region from the max-z surface to refine
        refinement_level: (int) number of refinement iterations, each iteration halves
            the mesh size
    """

    # get the bounding box of the case and update to only enclose refinement_depth
    bb_dict = construct_mesh_bounding_box_dict(case_dir)
    bb = bb_dict["bb"]
    bb[0][2] = max(bb[0][2], -refinement_depth)
    center = [
        0.5 * (bb[0][0] + bb[1][0]),
        0.5 * (bb[0][1] + bb[1][1]),
        0.5 * (bb[0][2] + bb[1][2]),
    ]

    # Update the refineLayerMeshDict parameters
    refine_layer_mesh_dict = f"{case_dir}/system/refineLayerMeshDict"
    update_parameter(
        refine_layer_mesh_dict,
        "geometry/refinementBox/min",
        f"( {bb[0][0]} {bb[0][1]} {bb[0][2]} )",
    )
    update_parameter(
        refine_layer_mesh_dict,
        "geometry/refinementBox/max",
        f"( {bb[1][0]} {bb[1][1]} {bb[1][2]} )",
    )
    update_parameter(
        refine_layer_mesh_dict,
        "castellatedMeshControls/locationInMesh",
        f"( {center[0]} {center[1]} {center[2]} )",
    )
    update_parameter(
        refine_layer_mesh_dict,
        "castellatedMeshControls/refinementRegions/refinementBox/levels",
        f"( ({refinement_level} {refinement_level}) )",
    )

    # Run snappyHexMesh and renumber mesh
    with working_directory(case_dir):
        os.system("snappyHexMesh -dict system/refineLayerMeshDict -overwrite")
    os.system(f"renumberMesh -case {case_dir} -overwrite")
