---
title: Myna Developer Guide
---

This guide focuses on extending Myna. For local validation details, see
[Testing](testing.md). For documentation maintenance, see
[Documentation](documentation.md).

## Local development workflow

Check that the current shell can find `uv` and has writable caches expected by the
repository:

```bash
python3 scripts/check_dev_tools.py
```

Install development dependencies from the repository root with:

```bash
uv sync --frozen --extra dev
```

Then rerun the preflight to verify that `pytest`, `ruff`, `mkdocs`, and `pre-commit`
are available through `uv run`:

```bash
python3 scripts/check_dev_tools.py
```

Some coding-agent and container shells do not inherit the same `PATH` or writable home
cache directories as an interactive terminal. If the preflight reports cache errors,
set writable cache locations before running `uv` or `pre-commit`:

```bash
export UV_CACHE_DIR=/tmp/uv-cache
export PRE_COMMIT_HOME=/tmp/pre-commit-cache
```

Run the default validation loop with:

```bash
uv run ruff format
uv run ruff check
uv run pytest
```

If you change dependencies, run `uv lock` and commit the updated `uv.lock`. If you
change documentation, run `uv run python scripts/check_docs_harness.py`; for MkDocs
pages, generate API docs with `uv run scripts/group_docs.py` and then run
`uv run mkdocs build --strict`.

## Developing new workflow components

The most common activity that will require development is implementing a new
workflow component to enable additional functionality. Before starting to implement
a new component you should answer several questions:

### Will this component require input files?

For example, a microstructure simulation may require thermal or solidification data.
If the component does require input files, then check if an existing `myna.core.files`
class exists with the required properties.

If there is no existing class, then you will have to implement a new `myna.core.files`
class. The `myna.core.files.FileVTK` is an example of a minimally
implemented class. It defines a file type (.vtk) and a basic check to determine if the
file is valid, i.e., if it has the extension of .vtk.

### What metadata does the component require from the build?

For example, a microstructure simulation would likely require the name of the material
to correctly set material properties. Check if existing classes for what you need
are defined in `myna.core.metadata`.

If class do not exist for one or more of required metadata values, then you will have
to make additional classes for each of the require metadata. There are two types of
metadata base classes, file-based and value-based metadata. The file-based metadata
base classes are defined in `myna.core.metadata.file` and define
file metadata as being associated with a build, a part, or a layer. The value-based
metadata base classes are defined in `myna.core.metadata.data` and
can be associated with a build or a part.

### What kind of file will the simulation output?

For example, a microstructure simulation may output a 3D volume of grain orientations.
Similar to the input files, check if an existing `myna.core.files` class exists with the
the required properties.

If there is no existing class, then you will have to create one. In addition to the
same considerations as input files, you may also want to implement `get_values_for_sync`
functionality if you intend for contents from that file to be uploaded back to the
database, however, this is optional (more on that later).

### Implementing the workflow component

With the above questions addressed, it is now time to implement a new component class.
An good example of a component class with the features mentioned above is
`myna.core.components.ComponentSolidificationPart`.
That class does not require a particular input file, it outputs a file class of `FileGV`
and requires several pieces of metadata. Additionally, it is associated with
layer-wise part simulations, hence the extension of the component types
`self.types.extend(["part", "layer"])`. The main functionality of components are
largely defined in the base Component class with the intention to keep implementing
new components fairly lightweight.

Once a new component is implemented, the `myna config` functionality will be enabled,
regardless of if there is an existing application. This will allow you to test that the
correct metadata is being supplied to the case directories. When composing your
input file, just provide an arbitrary name for the application, e.g., "test".

## Developing new applications

Once a new component is implemented, you will have to implement a corresponding
application (app) to use with `myna run`. Applications consist of up to three stage
modules:

1. `configure.py`: Module that configures the files within each Myna case folder
generated during `myna config`. At the end of this stage, each case folder should be a
valid case directory for whatever model is being run.
2. `execute.py`: Module that executes the model for each case.
3. `postprocess.py`: Module that converts the output of the model into the required
myna file format for the component. This may be part of `execute.py`, as well.

These stage modules are imported and called sequentially by `Component.run_component`.
Each module should define a function named for the stage (`configure`, `execute`, or
`postprocess`) or a `main()` function. The stages are mainly separated for clarity of
the app functionality and for handling runtime issues. *Technically* all functionality
can be in one stage, however, this may get confusing so it is recommended to split
functions into three stages. If the model is not Python-based, these stages can simply
wrap other commands as needed. All steps are optional and if one of these modules is
not present, it will be ignored.

Many of the already implemented apps use the `argparse` library to parse
user-specified inputs. In the input file, `configure`, `execute`, and
`postprocess` allow users to pass options to each stage for the app. Any parameters
that you wish to have accessible to users are intended to be adjusted through such
options, which are exposed to the active stage through `sys.argv` in the format
`--key value` or `--key` for Boolean flags. For Boolean flags, the assumed behavior is
False if the flag is not passed and True if the flag is passed.

Applications that derive from `MynaApp` should read workflow state from app attributes
such as `self.input_file`, `self.step_name`, `self.last_step_name`, and
`self.step_index`. Avoid reading `MYNA_*` environment variables directly in new app
code; those names remain only as a compatibility fallback for direct stage invocation.

Apps that wrap an external executable can query that executable's version with
`self.get_executable_version()`. Call it after parsing stage arguments so user-provided
`--exec`, `--env`, and Docker settings are available. For example:

```python
version = self.get_executable_version(
    "additiveFoam",
    version_args=[],
    version_regex=r"Version: (?P<version>\S+)",
)
```

The returned string can then be used to select a template or raise a clear
compatibility error.

It is likely that your app will require a `template` directory, or a set of input
files for your model that get copied into every case. If you are using a template
directory, then the intended functionality is that during `configure.py` the template
folder is copied into each of the case directory *and then updated*. Updating the files
inside the original template folder should be avoided.
