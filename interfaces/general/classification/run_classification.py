import classification
import classification.utilities
import classification.plotting
import classification.generator
import classification.training
import os
import numpy as np
from myna.workflow.load_input import load_input
import argparse
import sys
import yaml

def run_classification(settings, load_models=False, plot=True):

    # Make directory for classification, if needed, and change wokring directory to it
    orig_dir = os.getcwd()
    os.makedirs(settings["classification"]["output_dir_path"], exist_ok=True)
    os.chdir(settings["classification"]["output_dir_path"])

    # Create symbolic links to all available 3DThesis results.
    # This is to maintain compatibility with the directory
    # structurue that the classification package expects
    os.makedirs("3dthesis", exist_ok=True)
    for result in settings["3DThesis"]["results"]:
        copy_path = os.path.join("3dthesis", os.path.basename(result))
        if not os.path.exists(copy_path): os.symlink(result, copy_path)

    # Setup folder structure
    classification.utilities.folder_setup()

    # Generate voxel training data from 3DThesis data
    voxelTrainingData = classification.generator.make_voxel_training_data(plot=plot)

    # Train bnpy voxel classification model
    voxelData, voxelModelPath, nClusterV = classification.training.train_voxel_classifier(
                                                voxelTrainingData, 
                                                dpi=300, 
                                                loadModel=load_models, 
                                                plot=plot, 
                                                sF=0.5, 
                                                gamma=0.8,
                                                modelInitDir="randexamplesbydist")

    # Generate supervoxel training data from the voxel classification data
    supervoxelTrainingData = classification.generator.make_supervoxel_training_data(
        voxelModelPath, 
        voxelStep=0.0125, 
        supervoxelStep=0.25, 
        dpi=300, 
        plot=plot)

    # Train supervoxel classification model and generate plots of the classification results
    supervoxelDatasets, _, nClusterSV = classification.training.train_supervoxel_classifier(
                                                                    supervoxelTrainingData, 
                                                                    loadModel=load_models, 
                                                                    dpi=300, 
                                                                    plot=plot, 
                                                                    sF=0.5, 
                                                                    gamma=0.8,
                                                                    modelInitDir="randexamplesbydist")

    # Run post-processing plotting scripts
    if plot:
        nrows = int(np.floor(np.sqrt(nClusterV)))
        ncols = int(np.ceil(nClusterV/nrows))
        for id in range(len(supervoxelDatasets)):
            classification.plotting.combined_composition_colormesh(id, nrows=nrows, ncols=ncols, dpi=150)
    
    # Return to original working directory
    os.chdir(orig_dir)
    return [os.path.join(settings["classification"]["output_dir_path"], x) for x in supervoxelDatasets]

def main(argv=None):
    # Set up argparse
    parser = argparse.ArgumentParser(description='Launch classification for '+ 
                                     'specified input file')
    parser.add_argument('--input', type=str,
                        help='path to the desired input file to run' + 
                        ', for example: ' + 
                        '--input settings.yaml')
    parser.add_argument('--output', type=str,
                        help='path to the desired file to output results to' +
                        ', for example: ' +
                        '--output settings.yaml')
    args = parser.parse_args(argv)
    settings = load_input(args.input)
    settings["classification"]["results"] = run_classification(settings)
    print(settings["classification"]["results"])
    with open(args.output, "w") as f:
        yaml.dump(settings, f, default_flow_style=None)


if __name__ == "__main__":
    main(sys.argv[1:])