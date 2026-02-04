"""Script to generate and format Myna API docs using lazydocs. Intended to be
run from the root Myna repo directory during GitHub CI.
"""

import os
import shutil
from pathlib import Path

from lazydocs import generate_docs


def remove_global_variables(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    i0 = None
    i1 = None
    for i, line in enumerate(lines):
        if line == "**Global Variables**\n":
            i0 = i
        if (line == "---\n") and isinstance(i0, int):
            i1 = i
    if (i0 is not None) and (i1 is not None):
        newlines = lines[:i0] + lines[i1:]
        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(newlines)
        return True
    return False


def rename_module_heading_to_subpackage(filepath):
    """Returns True/False if the file is a subpackage header"""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if "# <kbd>module</kbd>" in line:
            lines[i] = line.replace("<kbd>module</kbd>", "<kbd>subpackage</kbd>")
            with open(filepath, "w", encoding="utf-8") as f:
                f.writelines(lines)


def write_awesome_pages_file(directory, group_name, overview_page_name="Overview"):
    """
    Creates a .pages file in the given directory to control MkDocs Awesome Pages.

    The .pages file will:
    - Explicitly set 'index.md' as the first link, named 'Overview'.
    - List all other .md files in the directory alphabetically afterwards.
    """

    # Set title for the section
    title = f"{group_name}"

    # Collect all non-index Markdown files and packages
    md_files = sorted(
        [
            f
            for f in os.listdir(directory)
            if Path(directory, f).is_file()
            and f.endswith(".md")
            and f != "index.md"
            and f != ".pages"
        ]
    )
    packages = sorted([f for f in os.listdir(directory) if Path(directory, f).is_dir()])

    # Start assembling the content in YAML format
    content = [f"title: {title}\n", "nav:\n"]

    # Add the index.md as the "Overview" landing page first (if it exists)
    if os.path.exists(Path(directory) / "index.md"):
        content.append(f'  - "{overview_page_name}": index.md\n')

    # Add all other collected module files and packages to the nav structure
    for md_file in md_files:
        content.append(f"  - {md_file}\n")
    for pkg in packages:
        content.append(f"  - {pkg}\n")

    # Write the .pages file
    pages_path = Path(directory) / ".pages"
    with open(pages_path, "w", encoding="utf-8") as f:
        f.writelines(content)


def group_api_docs(api_docs_dir: str | Path, base_package_name: str):
    """
    Groups generated Markdown files into subdirectories based on the
    first major module component (e.g., 'core' from 'my_package.core.utils.md').
    """

    # Iterate through all files
    files = sorted(os.listdir(api_docs_dir))
    for filename in files:
        src_path = Path(api_docs_dir, filename)
        module_parts = Path(filename).stem.split(".")
        is_subpackage = remove_global_variables(src_path)

        # Parse module name parts
        # myna.<pkg0>.<pkg1>.<...>.module.py
        if module_parts[0] == base_package_name:
            # Handle package index files
            if is_subpackage:
                target_dir = Path(api_docs_dir, *module_parts[1:])
                target_filename = "index.md"
                rename_module_heading_to_subpackage(src_path)
            # Parse target directory from the filename
            elif len(module_parts) > 2:
                # Handle all subpackages
                target_dir = Path(api_docs_dir, *module_parts[1:-1])
                target_filename = module_parts[-1] + ".md"
            elif len(module_parts) == 2:
                # Handle top-level packages
                target_dir = Path(api_docs_dir, module_parts[1])
                target_filename = module_parts[-1] + ".md"
            else:
                # Handle top-level modules
                target_dir = Path(api_docs_dir)
                target_filename = module_parts[-1] + ".md"

            # Move the file
            target_path = Path(target_dir, target_filename)
            os.makedirs(target_dir, exist_ok=True)
            print(f"{src_path.name} -> {target_path}")
            shutil.move(src_path, target_path)


if __name__ == "__main__":
    # Remove existing API docs and regenerate
    API_DIR = str(Path("docs", "api-docs").absolute())
    shutil.rmtree(API_DIR, ignore_errors=True)
    generate_docs(
        ["myna"],
        output_path=API_DIR,
        src_base_url="https://github.com/ORNL-MDF/Myna/blob/main",
    )

    # Run the grouping
    doc_dirs = group_api_docs(API_DIR, "myna")

    # Create pages for each directory
    for root, dirs, files in os.walk(API_DIR, topdown=True):
        group_name = Path(root).name
        if group_name == "api-docs":
            group_name = "API Documentation"
        write_awesome_pages_file(root, group_name)
        subpackage_index_file = Path(root, "index.md")
        if subpackage_index_file.exists():
            rename_module_heading_to_subpackage(subpackage_index_file)
