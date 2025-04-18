# 3DThesis application example for layer-wise solidification of a full part

To configure the example, first update the path to your 3DThesis executable by either:

- a) setting the path to the 3DThesis executable in the `steps:3dthesis:executable`
  entry in `input.yaml`
- b) setting the executable path under the `thesis:solidification_part:executable`
  entry in the example workspace `../example-workspace.yaml` and ensuring that the
  workspace file is set in the `myna:workspace` entry in `input.yaml`.

For instructions on building 3DThesis, see the documentation on the
[3DThesis repository](https://gitlab.com/JamieStumpORNL/3DThesis).

To run the example, enter:

```bash
myna config
myna run
myna sync
```

A variety of files will be generated. These are described in the list below.

- The "myna_resources" directory contains copies
of all the metadata that was required by the Myna workflow from the database.
- The "myna_output" directory contains all of the cases specified by the input file,
which include the input files for the case and the Myna-formatted output file.
- The database directory ("myna/examples/Peregrine"), contains new files in the
"registered" directory after the `myna sync` step that are the results from the
Myna simulation(s) converted to a format readable by Peregrine. Each field that is
output has both a .png file with the Peregrine pixel-level values and an .npz file
(numpy uncompressed binary archive) with the full-resolution data.
