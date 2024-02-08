# Interface documentation

- Component type 
  - `thermal_region_reduced_solidification`
- Interface name
  - `additivefoam_cube`
- Interface description 
  - Generate a cubic blockMesh surrounding
    the specified region center location with optional refinements
    in a given rectangular XY region surrounding the region center
    and in a given depth from the top of the layer.
- Example case
  - `examples/demo_thermal_region`

## Available options

To get available options for the `configure.py` and `execute.py` scripts, use the built-in help functions:
```
configure.py --help
execute.py --help
```