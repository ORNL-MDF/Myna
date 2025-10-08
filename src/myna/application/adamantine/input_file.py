"""Functions to read and write the input file for an adamantine case"""

from ast import literal_eval
from pathlib import Path
from myna.core.utils import nested_set


def input_file_to_dict(input_file: str | Path):
    """Loads an adamantine-style input file to a Python dictionary"""
    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Clean up text
    # - Remove leading/trailing whitespace and empty lines
    # - Delete comments
    lines = [line.strip('\t" "') for line in lines]
    lines = [line.split(";")[0].strip() for line in lines]
    lines = [line for line in lines if line.strip() != ""]

    input_dict = {}
    current_keys = []
    for line in lines:

        # Logically, do not need to know if entering a new dictionary
        if line == "{":
            continue

        # Step up a key
        if line == "}":
            _ = current_keys.pop()

        else:
            split_line = line.split(" ", maxsplit=1)
            if len(split_line) == 1:
                current_keys.append(split_line[0])
            else:
                line_key = [split_line[0]]
                line_literal = split_line[1]
                if line_literal in ["true", "false"]:
                    line_literal = line_literal.capitalize()
                try:
                    line_value = literal_eval(line_literal)
                except ValueError:
                    line_value = line_literal
                nested_set(input_dict, current_keys + line_key, line_value)

    return input_dict


def write_dict_to_input_file(input_dict: dict, input_file: str | Path):
    """Writes an adamantine input dictionary to the specified file"""
    # Assemble lines of the input file
    lines = []
    indent = ""

    def _append_values(lines, value_dict, indent):
        """Recursion for finding keys and values"""
        for _key, _value in value_dict.items():
            if isinstance(_value, dict):
                lines.append(f"{indent}{_key}\n")
                lines.append(f"{indent}" + "{\n")
                lines = _append_values(lines, value_dict[_key], indent + "  ")
                lines.append(f"{indent}" + "}\n")
            else:
                line_value = _value
                if isinstance(line_value, bool):
                    line_value = str(line_value).lower()
                lines.append(f"{indent}{_key} {line_value}\n")
        return lines

    lines = _append_values(lines, input_dict, indent)

    with open(input_file, "w", encoding="utf-8") as f:
        f.writelines(lines)


if __name__ == "__main__":
    # Test the functionality
    output = input_file_to_dict(
        Path(__file__).parent.resolve()
        / Path("temperature_part_pvd/template/input.info")
    )
    for key, value in output.items():
        print(key, value)
    write_dict_to_input_file(output, "test.txt")
