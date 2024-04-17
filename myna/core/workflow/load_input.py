import yaml


def load_input(filename):
    """Load input file into dictionary

    Args:
        filename: path to input file (str) to load

    Returns:
        settings: dictionary of input file settings
    """

    input_file = filename
    with open(input_file, "r") as f:
        file_type = input_file.split(".")[-1]
        if file_type.lower() == "yaml":
            settings = yaml.safe_load(f)
        else:
            print(
                f'ERROR: Unsupported input file type "{file_type}". Must be .yaml format'
            )

    return settings
