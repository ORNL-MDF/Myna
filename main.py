import run_autothesis
import run_classification
import run_rve_selection
import run_autofoam
import run_exaca
import json
import zipfile
import os
import yaml

if __name__ == "__main__":

    input_file = "settings.json"
    with open(input_file, "r") as f:
        file_type = input_file.split(".")[-1]
        if file_type == "json":
            settings = json.load(f)
        elif file_type == "yaml":
            settings = yaml.safe_load(f)
        else:
            print(f'ERROR: Unsupported input file type "{file_type}"')

    print("\nRunning autothesis...")
    results_autothesis = run_autothesis.run_autothesis(settings, check_for_existing_results=False)
    settings["3DThesis"]["results"] = results_autothesis
    print(f"Output files: {results_autothesis}")

    print("\nRunning classification...")
    results_classification = run_classification.run_classification(settings, load_models=False)
    settings["classification"]["results"] = results_classification
    print(f"Output: {results_classification}")

    print("\nRunning RVE selection...")
    results_rve = run_rve_selection.run_rve_selection(settings)
    settings["rve"]["results"] = results_rve
    print(f"Output: {results_rve}")

    print("\nRunning AutoFOAM case generation...")
    results_autofoam = run_autofoam.run_autofoam(settings, generate_cases=True)
    settings["autofoam"]["results"] = results_autofoam
    print(f"Output: {results_autofoam}")

    print("\nRunning ExaCA case generation...")
    results_exaca = run_exaca.create_cases(settings)
    print(f"Output: {results_exaca}")

    print("\nZipping AdditiveFOAM and ExaCA cases...")
    with zipfile.ZipFile(os.path.join("results", f"additivefoam_exaca_cases.zip"), mode="w") as archive:
        for case in results_autofoam:
            for root, dirs, files in os.walk(case):
                for name in files:
                    rel_path = os.path.join(root, name).split("results" + os.path.sep)[-1]
                    archive.write(os.path.join(root, name), rel_path)
        for case in results_exaca:
            for root, dirs, files in os.walk(case):
                for name in files:
                    rel_path = os.path.join(root, name).split("results" + os.path.sep)[-1]
                    archive.write(os.path.join(root, name), rel_path)
        for root, dirs, files in os.walk(os.path.join("resources","exaca","template")):
            for name in files:
                archive.write(os.path.join(root, name))
        for root, dirs, files in os.walk(os.path.join(".","resources","autofoam","template")):
            for name in files:
                archive.write(os.path.join(root, name))