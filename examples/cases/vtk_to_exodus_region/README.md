# Creep deformation simulation pipeline example

This example shows the coupling of process-structure-property simulations for creep deformation.

The pipeline contains the following simulations:

1. AdditiveFOAM: melt pool and resulting solidification thermal conditions
2. ExaCA: solidification grain growth
3. Cubit: meshing of microstructure
4. Deer: FEM crystal plasiticty simulation of the creep deformation

## Dependencies

AdditiveFOAM and ExaCA are available in the [containers](https://github.com/ORNL-MDF/containers) repository or can be built from source.

[Cubit](https://cubit.sandia.gov/) must be licensed appropriately.

Deer is an application built on the [MOOSE framework](https://mooseframework.inl.gov/).
It can be built on top of MOOSE containers,
and has been tested on the specific container mentioned in instructions below.

```sh
# If the first time setting this up on your system, create
# docker volume
docker volume create moose_projects

# Set BUILD_DIR to wherever you want to download moose repo
# > NOTE:
# > This will not actually be used in the Docker image,
# > but it is needed to get the correct version of the image
export BUILD_DIR=$HOME
cd $BUILD_DIR
git clone https://github.com/idaholab/moose.git
cd moose
git checkout 2025-05-09-release
export MOOSE_DEV_VERSION=$(./scripts/versioner.py moose-dev)
docker pull idaholab/moose-dev:$MOOSE_DEV_VERSION

# Start an container instance of the moose-dev image,
# will download the image if not available locally
docker run -it -v moose_projects:/projects idaholab/moose-dev:$MOOSE_DEV_VERSION
```

```sh
# ------------------------- #
# in the moose-dev instance #
# ------------------------- #
# Set useful vars
export BUILD_DIR="/projects" # where volume is mounted

# If the first time attaching to the volume, set up the moose repo
# Moose tag must correspond to the version that set MOOSE_DEV_VERSION
cd $BUILD_DIR
git clone https://github.com/idaholab/moose.git
cd moose
git checkout 2025-05-09-release

# Test that moose is working
# > NOTE:
# > For some reason the moose-dev Docker container doesn't seem to
# > contain all the needed Python dependencies
#
# > NOTE:
# > It is possible to get a "g++: fatal error: Killed signal
# > terminated program cc1plus" error, potentially related to
# > using too much memory during compilation. Make sure to specify
# > a number of processes during compiling, e.g., `make -j4`
cd ${BUILD_DIR}/moose/test
make -j4
./run_tests

# Clean the moose build to make sure it uses the shipped MPI
# implementation
find ${BUILD_DIR}/moose -name "*.la" -o -name "*.lo" | wc -l
find ${BUILD_DIR}/moose -name "*.la" -delete
find ${BUILD_DIR}/moose -name "*.lo" -delete
rm -rf ${BUILD_DIR}/moose/framework/.libs ${BUILD_DIR}/moose/framework/.deps 2>/dev/null || true

# Get NEML and Deer
cd $BUILD_DIR
git clone https://github.com/Argonne-National-Laboratory/deer.git
cd deer
git clone https://github.com/Argonne-National-Laboratory/neml.git
cd neml
git checkout 65c2ee4
cd $BUILD_DIR/deer/neml

# Fix CMakeLists.txt which has a bug in the Deer-specified NEML commit
sed -i 's/set(CMAKE_C_FLAGS ${CMAKE_C_FLAGS} ${OpenMP_C_FLAGS})/set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} ${OpenMP_C_FLAGS}")/' CMakeLists.txt
sed -i 's/set(CMAKE_CXX_FLAGS ${CMAKE_CXX_FLAGS} ${OpenMP_CXX_FLAGS})/set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${OpenMP_CXX_FLAGS}")/' CMakeLists.txt

# Build NEML, needing to specify BLAS and LAPACK paths manually
rm -r build
mkdir build
cd build
cmake .. -DCMAKE_BUILD_TYPE="Release" -DBLAS_LIBRARIES="$CONDA_PREFIX/lib/libblas.so" -DLAPACK_LIBRARIES="$CONDA_PREFIX/lib/liblapack.so"
make -j16

# The Deer make has neml/lib hardcoded somewhere, so symlink it
# to the expected path
ln -s ./lib ../lib

# Set all flags and build Deer
# > NOTE:
# > Tests might fail, but the example runs
cd ../..
export DEER_DIR=${BUILD_DIR}/deer
export LDFLAGS="$LDFLAGS -L${BUILD_DIR}/deer/neml/build/lib -Wl,-rpath,${BUILD_DIR}/deer/neml/build/lib"
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:${BUILD_DIR}/deer/neml/lib
export MOOSE_DIR=${BUILD_DIR}/moose
make -j16
```
