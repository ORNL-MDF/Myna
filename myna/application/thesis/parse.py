import shutil
import os


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
