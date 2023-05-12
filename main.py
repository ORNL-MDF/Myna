import run_autothesis
import run_classification
import run_rve_selection
import json

if __name__ == "__main__":

    with open("settings.json", "r") as f:
        settings = json.load(f)

    print("\nRunning autothesis...")
    results_autothesis = run_autothesis.run_autothesis(settings, check_for_existing_results=True)
    settings["3DThesis"]["results"] = results_autothesis
    print(f"Output files: {results_autothesis}")

    print("\nRunning classification...")
    results_classification = run_classification.run_classification(settings, load_models=True)
    settings["classification"]["results"] = results_classification
    print(f"Output: {results_classification}")

    print("\nRunning RVE selection...")
    results_rve = run_rve_selection.run_rve_selection(settings)
    print(f"Output: {results_rve}")