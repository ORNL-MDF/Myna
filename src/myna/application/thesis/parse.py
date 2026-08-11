#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import shutil
import os
from pathlib import Path


def load_file_lines(filepath, newline="\n"):
    with open(filepath, "r+") as f:
        # Read file
        file_contents = f.read()
        file_lines = file_contents.split(newline)

    return file_lines


def find_keyword_line_indices(file_lines, keyword, filepath):
    kwrd_line_indices = [ind for ind, x in enumerate(file_lines) if keyword in x]

    # Output error if keyword not found
    if len(kwrd_line_indices) < 1:
        print("Error -> Keyword(s) Found")
        print("Function -> adjust_parameter")
        print("File: ", filepath)
        print("Keyword: ", keyword)
        exit(1)

    return kwrd_line_indices


def adjust_parameter(filepath, keyword, value):
    """Updates keyword value for 3DThesis input file

    Keyword arguments:
    filepath -- filepath for the 3DThesis file to update
    keyword -- keyword value to update in specified file
    value -- value to update keyword to
    """

    file_lines = load_file_lines(filepath)
    kwrd_line_indices = find_keyword_line_indices(file_lines, keyword, filepath)

    # Update the value for the keyword entry
    updated_line = f"\t{keyword}\t{value}"
    for i in kwrd_line_indices:
        file_lines[i] = updated_line

    # Write file out
    with open(filepath, "w") as f:
        file_contents = "\n".join(file_lines)
        f.write(file_contents)
        f.truncate()


def read_parameter(filepath, keyword):
    """Read the specified keyword value from file"""

    # Get file lines and keyword indices
    file_lines = load_file_lines(filepath)
    kwrd_line_indices = find_keyword_line_indices(file_lines, keyword, filepath)

    # Extract value from line
    values = []
    for i in kwrd_line_indices:
        values.append(" ".join(file_lines[i].split(keyword)[-1].split()))

    return values


def copy_simulation_result(
    new_file,
    result_file=os.path.join("3DThesis", "TestInputs", "Data", "TestSim.Final.csv"),
):
    """Copies final simulation results to the specified folder"""

    os.makedirs(os.path.dirname(new_file), exist_ok=True)
    shutil.copy(result_file, new_file)

    return new_file


def update_domain_resolution(domain_file, direction, value):
    """Update the mesh resolution for one direction in a Thesis Domain file."""
    direction = direction.upper()
    if direction not in {"X", "Y", "Z"}:
        raise ValueError(
            f"Unsupported Thesis Domain direction '{direction}'. Expected X, Y, or Z."
        )

    file_lines = load_file_lines(domain_file)
    direction_line = None
    for ind, line in enumerate(file_lines):
        if line.strip() == direction:
            direction_line = ind
            break

    if direction_line is None:
        raise ValueError(
            f"Could not find Thesis Domain direction '{direction}' in {domain_file}."
        )

    in_block = False
    for ind in range(direction_line + 1, len(file_lines)):
        line = file_lines[ind].strip()
        if line == "{":
            in_block = True
            continue
        if in_block and line == "}":
            break
        if in_block and line.startswith("Res"):
            file_lines[ind] = f"\tRes\t{value}"
            with open(domain_file, "w", encoding="utf-8") as f:
                f.write("\n".join(file_lines))
                f.truncate()
            return

    raise ValueError(
        f"Could not find a Res entry for Thesis Domain direction '{direction}' "
        f"in {domain_file}."
    )


def write_file_lines(filepath, file_lines, newline="\n"):
    """Write newline-stripped lines back to a file."""
    Path(filepath).write_text(newline.join(file_lines) + newline, encoding="utf-8")


def replace_first_nonempty_line(filepath, new_value):
    """Replace the first non-empty line in a Thesis text input file."""
    file_lines = load_file_lines(filepath)
    for index, line in enumerate(file_lines):
        if line.strip():
            file_lines[index] = new_value
            write_file_lines(filepath, file_lines)
            return
    raise ValueError(f"Could not find a non-empty line in {filepath}")


def find_named_block(filepath, block_name):
    """Return the content bounds for a simple named Thesis block."""
    file_lines = load_file_lines(filepath)
    for index, line in enumerate(file_lines):
        if line.strip() != block_name:
            continue
        brace_index = None
        for candidate in range(index + 1, len(file_lines)):
            stripped = file_lines[candidate].strip()
            if not stripped:
                continue
            if stripped == "{":
                brace_index = candidate
                break
            raise ValueError(f"Expected '{{' after block {block_name} in {filepath}.")
        if brace_index is None:
            break
        for end_index in range(brace_index + 1, len(file_lines)):
            if file_lines[end_index].strip() == "}":
                return file_lines, brace_index + 1, end_index
    raise ValueError(f"Could not find block {block_name} in {filepath}.")


def set_block_keyword(filepath, block_name, keyword, value):
    """Update or append one keyword within a simple Thesis block."""
    file_lines, start_index, end_index = find_named_block(filepath, block_name)
    updated_line = f"\t{keyword}\t{value}"
    for index in range(start_index, end_index):
        tokens = file_lines[index].strip().split()
        if tokens and tokens[0] == keyword:
            file_lines[index] = updated_line
            write_file_lines(filepath, file_lines)
            return
    file_lines.insert(end_index, updated_line)
    write_file_lines(filepath, file_lines)


def remove_block_keyword(filepath, block_name, keyword):
    """Remove one keyword from a simple Thesis block when it exists."""
    file_lines, start_index, end_index = find_named_block(filepath, block_name)
    filtered_lines = []
    removed = False
    for index, line in enumerate(file_lines):
        if start_index <= index < end_index:
            tokens = line.strip().split()
            if tokens and tokens[0] == keyword:
                removed = True
                continue
        filtered_lines.append(line)
    if removed:
        write_file_lines(filepath, filtered_lines)
