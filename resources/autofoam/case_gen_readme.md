# Case generation
To set up your environment and generate the AdditiveFOAM cases, use the following example code as a template.

## ExaCA
The ExaCA input files are also included and need to be updated with the correct absolute file paths. Two tokens are used in the myna_test case, MYNA_SIM_PATH and EXACA_EXE_PATH. These need to be replaced with the appropriate paths before running the simulations. You can do this using the following script as a template.

```bash
#!/bin/bash

original_string="EXACA_EXE_PATH"
new_string="/home/path/to/exe"

sed -i "s|$original_string|$new_string|g" your_file.txt
```

## Example for generating AdditiveFOAM cases

Frontier:

```bash
# Setup python environment
module load cray-python
python -m venv ve_myna
source ./ve_myna/bin/activate
pip install -U pip

# Install autofoam to python environment
git clone https://code.ornl.gov/8s2/autofoam.git # enter credentials to clone
git switch remove-foam-dep
git checkout d3c2cace543a02d471beb3413dee78d5e64e8324
cd autofoam
pip install -e .

# Generate AdditiveFoam cases
cd ..
unzip myna_test.zip -d ./myna_test
cd myna_test
python autofoam_case_gen.py

```