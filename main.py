import run_autothesis
import run_classification

if __name__ == "__main__":

    print("\nRunning autothesis...")
    result = run_autothesis.run_autothesis()
    print(f"Output: {result}")

    print("\nRunning classification...")
    result = run_classification.run_classification()
    print(f"Output: {result}")