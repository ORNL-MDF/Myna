#!/bin/bash

#SBATCH -p asina
#SBATCH -J k_02_3a
#SBATCH -o log.out
#SBATCH -e log.err

#SBATCH --nodes 1
#SBATCH --ntasks-per-node 32
#SBATCH --mem=0

#SBATCH --cpus-per-task 1

cd $SLURM_SUBMIT_DIR

module purge
module load mpi/openmpi-4.1.1-pmix
source /home/8s2/OpenFOAM/OpenFOAM-8/etc/bashrc

run_openfoam="srun --exclusive --mem=0 -N 1 -n 32 additiveFoam -parallel"

for d in case_3a/1
do
    (
        echo "Running case: $d"
        cd $d
        decomposePar -force > "log.decomposePar" 2>&1
        $run_openfoam > "log.additiveFoam" 2>&1
    ) &
done

wait
