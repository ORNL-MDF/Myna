# Example: AdditiveFOAM Single Track Calibration

This example covers how to calibrate an AdditiveFOAM
[projectedGaussian](https://github.com/ORNL/AdditiveFOAM/blob/main/applications/solvers/additiveFoam/movingHeatSource/heatSourceModels/projectedGaussian/projectedGaussian.C)
heat source using experimental measurements of single track melt pool depths.

## Myna case setup

This example requires the following files:

- `input.yaml`: the Myna input file
- `experiments.yaml`: single track measurements required by the AdditiveFOAM single
  track calibration app

This use case is a little different than other examples, because the
`additivefoam/single_track_calibration` app does not require any build metadata and
is not associated with any build region, part or layer. Instead, the app is entirely
dependent on the file specified in the "configure/experiments" step parameter in the
Myna input file. The experiments file is a list of entries under a "data" entry
following the format:

```yaml
data:
  - process_parameters:
      power: 187.5      # Laser power, in Watts
      scan_speed: 0.5   # Scan speed of the laser, in meters/second
      spot_size: 0.1    # Spot size (diameter), in millimeters
      material: SS316L  # name of material, corresponding to Myna material library
    depths: [91.0e-3]   # list of depth values corresponding to the process parameters, in millimeters
  - ... # repeat for additional process parameters
```

Because no build data is requires, the input file does not need to have a "data" entry.
While this entry will be populated in the configured input file, it will have
empty values for all of its fields. The default output directory `myna_output` will
be created for writing the results of the workflow step. If you want to change this
behavior, you have to set the `input["data"]["build"]["name"]` entry to the desired
outputlocation. If you have other steps in the workflow that do require build data,
then you will need to specify an appropriate database entry.

## Description of the AdditiveFOAM application

The AdditiveFOAM application workflow consists of the following steps:

1. *Load experimental data*: Parse the experimental data for depth measurements as a
   function of process parameters
2. *Identify missing simulations*: If simulations are already detected in the output
   directory, then they will be loaded and only missing simulations will be run.
3. *Run required simulations*: Single track simulations are configured and run in
   `sim_output` within the Myna step directory. A hashed "fingerprint" of the process
   parametersis used to group simulations with the same process parameters
   (but different simulation parameters, i.e., n-values), so simulations will be grouped
   into directories with long "random" names.
4. *Performing Bayesian calibration from n-values*: Based on the simulated depth, optimal
   n-values for each process parameter will be calculated using a Bayesian calibration
   approach leveraging the [pymc](https://www.pymc.io/) package.
5. *Performing Bayesian calibration for heat-source parameters*: All of the calibrated
   n-values are assembled to find optimized heat source parameters for the
   `projectedGaussian` heat source given the experimentally-measured values, again
   using `pymc` methods.

The results of the calibration are stored in the Myna-style output, which for this
example will be: "myna_output/calibrate_additivefoam_heatsource/single_track_calibration-calibrate_additivefoam_heatsource-FileYAML.yaml"
