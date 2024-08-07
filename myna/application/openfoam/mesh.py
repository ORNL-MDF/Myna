#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import os
import re
import subprocess
import vtk


def preprocess_stl(case_dir, stl_path, convert_to_meters=1):
    """creates a copy of the stl file"""
    """ converts stl to meters """
    """ cleans the copied stl file to the template directory """
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
    surfaceFeaturesDict = f"{case_dir}/system/surfaceFeaturesDict"

    os.system(
        f"foamDictionary -entry surfaces -set '(\"{stl_file_name}\")' {surfaceFeaturesDict}"
    )

    os.system(f"surfaceFeatures -case {case_dir}")

    eMesh_name = stl_file_name.split(".")[0] + ".eMesh"

    # update entries is snappyHexMeshDict
    snappyHexMeshDict = f"{case_dir}/system/snappyHexMeshDict"
    origin = " ".join(list(map(str, origin)))
    print("origin for stl features: ", origin)

    os.system(
        f"foamDictionary -entry geometry/part/file"
        f""" -set '"{stl_file_name}"' {snappyHexMeshDict}"""
    )

    os.system(
        f"foamDictionary -entry castellatedMeshControls/features"
        f""" -set '( {"{"} file "{eMesh_name}"; level {refinement_level}; {"}"} )' """
        f"{snappyHexMeshDict}"
    )

    os.system(
        f"foamDictionary -entry castellatedMeshControls/locationInMesh"
        f" -set '( {origin} )' {snappyHexMeshDict}"
    )

    os.system(
        f"foamDictionary -entry castellatedMeshControls/refinementSurfaces/part/level"
        f" -set '( {refinement_level} {refinement_level} );' {snappyHexMeshDict}"
    )

    os.system(
        f"foamDictionary -entry castellatedMeshControls/refinementRegions/part/levels"
        f" -set '( ({refinement_level} {refinement_level}) );' {snappyHexMeshDict}"
    )


def create_background_mesh(case_dir, working_stl_path, spacing, tolerance):
    """create a background mesh using blockMesh around the stl file"""

    # get the bounding box of the stl to create background mesh
    s = subprocess.check_output(
        f"surfaceCheck {working_stl_path} | grep -i 'Bounding Box :'", shell=True
    ).decode("utf-8")
    bb_str = re.findall("\(([^)]+)", s)

    bb_min = [float(x) - tolerance for x in bb_str[0].split(" ")]
    bb_max = [float(x) + tolerance for x in bb_str[1].split(" ")]
    bb = bb_min + bb_max
    bbDict = {"bb_min": bb_min, "bb_max": bb_max, "bb": bb}

    # set the number of cells in each direction based on the desired spacing
    span = [b - a for (a, b) in zip(bb_min, bb_max)]
    nCells = [round(a / b) for (a, b) in zip(span, spacing)]
    origin = [a + b / 2.0 for (a, b) in zip(bb_min, span)]

    # update the background mesh file
    blockMeshDict = os.path.join(case_dir, "system/blockMeshDict")
    lines = open(blockMeshDict, "r").readlines()

    keys = ["xmin", "ymin", "zmin", "xmax", "ymax", "zmax"]

    for k, key in enumerate(keys):
        for i, line in enumerate(lines):
            if line.startswith(key):
                token = line.replace(";", "").split()[-1]
                lines[i] = line.replace(token, str(bb[k]))

    keys = ["nx", "ny", "nz"]

    for k, key in enumerate(keys):
        for i, line in enumerate(lines):
            if line.startswith(key):
                token = line.replace(";", "").split()[-1]
                lines[i] = line.replace(token, str(nCells[k]))

    with open(blockMeshDict, "w") as f:
        for line in lines:
            f.write(str(line))

    os.system(f"blockMesh -case {case_dir}")

    return origin, bbDict


def create_part_mesh(case_dir, stl_path, bbDict, mpi_args=None):
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

        os.system(
            f"foamDictionary -entry numberOfSubdomains"
            f" -set {nprocs} {case_dir}/system/decomposeParDict"
        )

        os.system(f"decomposePar -case {case_dir} -force")

        os.system(f"{mpi_args} snappyHexMesh -case {case_dir} -parallel -overwrite")

        os.system(f"reconstructParMesh -case {case_dir} -withZero -constant")

        os.system(f"rm -rf {case_dir}/processor*")

    # move bottom of mesh to z=0 plane
    translation = " ".join(str(t) for t in [0, 0, -bbDict["bb_min"][2]])
    os.system(f'transformPoints -case {case_dir} "translate=({translation})"')

    # save a copy of polyMesh for the part in the working directory
    stl_file_name = os.path.basename(stl_path)
    polyMesh_copy = f"{case_dir}/{stl_file_name.split('.')[0]}.polyMesh"
    os.system(f"cp -rf {case_dir}/constant/polyMesh {polyMesh_copy}")


def create_cube_mesh(case_dir, spacing, tolerance, rve, rve_pad):
    """create a cube mesh at the specified rve location"""

    # get the bounding box of the stl to create block mesh
    bb_min = [rve[0][0] - rve_pad[0], rve[0][1] - rve_pad[1], rve[0][2] - rve_pad[2]]
    bb_max = [rve[1][0] + rve_pad[0], rve[1][1] + rve_pad[1], rve[1][2]]
    bb = bb_min + bb_max
    bbDict = {"bb_min": bb_min, "bb_max": bb_max, "bb": bb}

    # set the number of cells in each direction based on the desired spacing
    span = [b - a for (a, b) in zip(bb_min, bb_max)]
    nCells = [round(a / b) for (a, b) in zip(span, spacing)]
    origin = [a + b / 2.0 for (a, b) in zip(bb_min, span)]

    # update the background mesh file
    blockMeshDict = os.path.join(case_dir, "system/blockMeshDict")
    lines = open(blockMeshDict, "r").readlines()

    keys = ["xmin", "ymin", "zmin", "xmax", "ymax", "zmax"]

    for k, key in enumerate(keys):
        for i, line in enumerate(lines):
            if line.startswith(key):
                token = line.replace(";", "").split()[-1]
                lines[i] = line.replace(token, str(bb[k]))

    keys = ["nx", "ny", "nz"]

    for k, key in enumerate(keys):
        for i, line in enumerate(lines):
            if line.startswith(key):
                token = line.replace(";", "").split()[-1]
                lines[i] = line.replace(token, str(nCells[k]))

    with open(blockMeshDict, "w") as f:
        for line in lines:
            f.write(str(line))

    os.system(f"blockMesh -case {case_dir}")

    return [origin, bbDict]


def foam_to_adamantine(case_dir, precision=8):
    """convert OpenFOAM VTK format to adamantine VTK format"""

    # Create OpenFOAM VTK file
    os.system(f"foamToVTK -case {case_dir} -constant -ascii")
    vtk_file_path = os.path.join(case_dir, "VTK", os.path.basename(case_dir) + "_0.vtk")

    # Read the OpenFOAM VTK file
    reader = vtk.vtkUnstructuredGridReader()
    reader.SetFileName(vtk_file_path)
    reader.Update()
    grid = reader.GetOutput()

    # Write the Adamantine VTK file
    with open(vtk_file_path, "w") as f:
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
        id_list = vtk.vtkIdList()
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


def slice(case_dir, height):
    """slice the part mesh at a specified build height"""
    s = subprocess.check_output(
        f"checkMesh -case {case_dir} -noTopology | grep -i 'Overall domain bounding box'",
        shell=True,
    ).decode("utf-8")

    bb_str = re.findall("\(([^)]+)", s)

    bb_min = [float(x) - 1e-8 for x in bb_str[0].split(" ")]
    bb_max = [float(x) + 1e-8 for x in bb_str[1].split(" ")]
    bb = bb_min + bb_max
    bb[-1] = height

    topoSetDict = f"{case_dir}/system/topoSetDict"
    lines = open(topoSetDict, "r").readlines()

    keys = ["xmin", "ymin", "zmin", "xmax", "ymax", "zmax"]

    for k, key in enumerate(keys):
        for i, line in enumerate(lines):
            if line.startswith(key):
                token = line.replace(";", "").split()[-1]
                lines[i] = line.replace(token, str(bb[k]))

    with open(topoSetDict, "w") as f:
        for line in lines:
            f.write(str(line))

    # remove the created cellSet and renumber new mesh
    os.system(f"topoSet -case {case_dir}")
    os.system(f"subsetMesh -case {case_dir} -overwrite c0 -patch part")
    os.system(f"rm -rf {case_dir}/constant/polyMesh/sets")
    os.system(f"rm -rf {case_dir}/constant/polyMesh/*Level")
    os.system(f"renumberMesh -case {case_dir} -overwrite")

    # align the sliced mesh with the top at z=0 plane
    s = subprocess.check_output(
        f'checkMesh -case {case_dir} -noTopology | grep -i "Overall domain bounding box"',
        shell=True,
    ).decode("utf-8")

    zmax = float(re.findall("\(([^)]+)", s)[-1].split(" ")[-1])
    translation = " ".join(list(map(str, [0, 0, -zmax])))
    os.system(f'transformPoints -case {case_dir} "translate=({translation})"')


def refine_RVE(case_dir, bb):
    os.system(
        f"foamDictionary -entry box -set "
        f'"( {bb[0][0]} {bb[0][1]} {bb[0][2]} ) '
        f'( {bb[1][0]} {bb[1][1]} {bb[1][2]} )" '
        f"{case_dir}/constant/foamToExaCADict"
    )

    os.system(
        f"foamDictionary -entry geometry/refinementBox/min "
        f'-set "( {bb[0][0]} {bb[0][1]} {bb[0][2]} )" '
        f"{case_dir}/system/refineMeshDict"
    )

    os.system(
        f"foamDictionary -entry geometry/refinementBox/max "
        f'-set "( {bb[1][0]} {bb[1][1]} {bb[1][2]} )" '
        f"{case_dir}/system/refineMeshDict"
    )

    center = [
        0.5 * (bb[0][0] + bb[1][0]),
        0.5 * (bb[0][1] + bb[1][1]),
        0.5 * (bb[0][2] + bb[1][2]),
    ]

    os.system(
        f"foamDictionary -entry castellatedMeshControls/locationInMesh "
        f'-set "( {center[0]} {center[1]} {center[2]} )" '
        f"{case_dir}/system/refineMeshDict"
    )

    os.system(f"cd {case_dir} && snappyHexMesh -dict system/refineMeshDict -overwrite")


def refine_layer(case_dir, refinement_depth, refinement_level):

    # get the bounding box of the stl to create background mesh
    s = subprocess.check_output(
        f"checkMesh -case {case_dir} -noTopology | grep -i 'Overall domain bounding box'",
        shell=True,
    ).decode("utf-8")

    bb_str = re.findall("\(([^)]+)", s)

    bb_min = [float(x) - 1e-8 for x in bb_str[0].split(" ")]
    bb_max = [float(x) + 1e-8 for x in bb_str[1].split(" ")]
    bb = [bb_min, bb_max]

    bb[0][2] = max(bb[0][2], -refinement_depth)

    os.system(
        f"foamDictionary -entry geometry/refinementBox/min "
        f'-set "( {bb[0][0]} {bb[0][1]} {bb[0][2]} )" '
        f"{case_dir}/system/refineLayerMeshDict"
    )

    os.system(
        f"foamDictionary -entry geometry/refinementBox/max "
        f'-set "( {bb[1][0]} {bb[1][1]} {bb[1][2]} )" '
        f"{case_dir}/system/refineLayerMeshDict"
    )

    center = [
        0.5 * (bb[0][0] + bb[1][0]),
        0.5 * (bb[0][1] + bb[1][1]),
        0.5 * (bb[0][2] + bb[1][2]),
    ]

    os.system(
        f"foamDictionary -entry castellatedMeshControls/locationInMesh "
        f'-set "( {center[0]} {center[1]} {center[2]} )" '
        f"{case_dir}/system/refineLayerMeshDict"
    )

    os.system(
        f"foamDictionary -entry castellatedMeshControls/refinementRegions/refinementBox/levels"
        f' -set "( ({refinement_level} {refinement_level}) );" '
        f"{case_dir}/system/refineLayerMeshDict"
    )

    os.system(
        f"cd {case_dir} && snappyHexMesh -dict system/refineLayerMeshDict -overwrite"
    )
    os.system(f"renumberMesh -case {case_dir} -overwrite")
