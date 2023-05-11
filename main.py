import run_autothesis
import run_classification
import json

if __name__ == "__main__":

    with open("settings.json", "r") as f:
        settings = json.load(f)

    print("\nRunning autothesis...")
    result = run_autothesis.run_autothesis(settings)
    print(f"Output: {result}")

    print("\nRunning classification...")
    result = run_classification.run_classification(settings)
    print(f"Output: {result}")