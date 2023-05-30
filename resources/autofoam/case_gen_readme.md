# Case generation
To set up your environment and generate the AdditiveFOAM cases, use the following example code as a template.


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
unzip additivefoam_exaca_cases -d ./myna_cases
cd myna_cases/autofoam
python autofoam_case_gen.py

```