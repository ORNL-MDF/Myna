# Developer Guide

To install developer-related Python packages, follow the instructions in
the [main project README](../README.md##installation).

## Developing new workflow components

The most common activity that will require development is implementing a new
workflow component to enable additional functionality. Before starting to implement
a new component you should answer several questions:

### Will this component require input files?

For example, a microstructure simulation may require thermal or solidification data.
If the component does require input files, then check if an existing `myna.files`class
exists with the required properties.

If there is no existing class, then you will have to implement a new `myna.files` class.
The [FileVTK](../src/myna/files/file_vtk.py) is an example of a minimally implemented
class. It defines a file type (.vtk) and a basic check to determine if the file is valid
(is the extension of the file .vtk).

### What metadata does the component require from the build?

For example, a microstructure simulation would likely require the name of the material
to correctly set material properties. Check if existing classes for what you need
are defined in `myna.metadata`.

If class do not exist for one or more of required metadata values, then you will have
to make additional classes for each of the require metadata. There are two types of
metadata base classes, file-based and value-based metadata. The file-based metadata
base classes are defined in [file.py](../src/myna/metadata/file.py) and define
file metadata as being associated with a build, a part, or a layer. The value-based
metadata base classes are defined in [data.py](../src/myna/metadata/data.py) and
can be associated with a build or a part.

### What kind of file will the simulation output?

For example, a microstructure simulation may output a 3D volume of grain orientations.
Similar to the input files, check if an existing `myna.files` class exists with the
the required properties.

If there is no existing class, then you will have to create one. In addition to the
same considerations as input files, you may also want to implement `get_values_for_sync`
functionality if you intend for contents from that file to be uploaded back to the
database, however, this is optional (more on that later).

### Implementing the workflow component

With the above questions addressed, it is now time to implement a new component class.
An good example of a component class with the features mentioned above is
[ComponentSolidificationPart](../src/myna/components/component_solidification.py)
That class does not require a particular input file, it outputs a file class of `FileGV`
and requires several pieces of metadata. Additionally, it is associated with
layer-wise part simulations, hence the extension of the component types
`self.types.extend(["part", "layer"])`. The main functionality of components are
largely defined in the base Component class with the intention to keep implementing
new components fairly lightweight.

Once a new component is implemented, the `myna_config` functionality will be enabled,
regardless of if there is an existing interface. This will allow you to test that the
correct metadata is being supplied to the case directories. When composing your
input file, just provide an arbitrary name for the interface, e.g., "test".

## Developing new interfaces

Once a new component is implemented, you will have to implement a corresponding
interface to use with `myna_run`. Interfaces consist of up to three scripts:

1. `config.py`: Script that configures the files within each Myna case folder generated
during `myna_config`. At the end of this script, each case folder should be a valid
case directory for whatever model is being run.
2. `execute.py`: Script that executes the model for each case.
3. `postprocess.py`: Script that converts the output of the model into the required
myna file format for the component. This may be part of execute.py, as well.

These scripts are run sequentially and are mainly separated for clarity of the interface
functionality and for handling runtime issues. *Technically* all functionality can
be in one script, however, this may get confusing so it is recommended to split
functions into three scripts. If the model is not Python-based, these scripts can
simply wrap other scripts as needed. All steps are optional and if one of these
scripts is not present, it will be ignored.

Many of the already implemented interfaces use the `argparse` library to parse
user-specified inputs. In the input file, `configure`, `execute`, and
`postprocess` allow users to pass options to each of the scripts
for the interface. Any parameters that you wish to have accessible to users are
intended to be adjusted through such options, which are passed to the script via
command line in the format `--key value` or `--key` for Boolean flags. For Boolean
flags, the assumed behavior is False if the flag is not passed and True if the flag is
passed.

It is likely that your interface will require a `template` directory, or a set of input
files for your model that get copied into every case. If you are using a template
directory, then the intended functionality is that during `config.py` the template
folder is copied into each of the case directory *and then updated*. Updating the files
inside the template folder should be avoided.
