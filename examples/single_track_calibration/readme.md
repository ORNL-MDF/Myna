# Example: AdditiveFOAM Single Track Calibration

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
