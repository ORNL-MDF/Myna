import sys
import os
import subprocess
import datetime
import contextlib
from pathlib import Path
import yaml
import myna.utils


@contextlib.contextmanager
def working_directory(path):
    """
    Changes working directory and returns to previous on exit.

    Reference:
    - https://stackoverflow.com/questions/41742317/how-can-i-change-directory-with-python-pathlib
    """
    prev_cwd = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


def launch_from_peregrine(argv=sys.argv):
    # Set working directory to the peregrine_launcher interface
    peregrine_launcher_path = os.path.join(
        os.environ["MYNA_INSTALL_PATH"], "cli", "peregrine_launcher"
    )
    with working_directory(peregrine_launcher_path):
        # Parse the arguments passed from Peregrine
        build_path = argv[1]
        layers = [int(x) for x in myna.utils.strlist_to_list(argv[2])]
        exported_parts = myna.utils.strlist_to_list(argv[3])
        resolution = float(argv[4])
        mode = argv[5].lower()

        # Write Peregrine input to log file
        lines = []
        lines.append(f"""argv = {argv[0]} {' '.join([f'"{x}"' for x in argv[1:]])}\n""")
        lines.append(f"{build_path=}\n")
        lines.append(f"{layers=}\n")
        lines.append(f"{exported_parts=}\n")
        lines.append(f"{resolution=}\n")
        lines.append(f"{mode=}\n")

        # Get yyyy-mm-dd_hh-mm format for the current time and add to log file
        now = datetime.datetime.now()
        now_str_pretty = now.strftime("%Y-%m-%d %H:%M:%S")
        now_str_id = now.strftime("%Y-%m-%d-%Hh-%Mm")
        lines.append(f"\nSimulation started at {now_str_pretty}\n")

        # Set input file paths
        input_file = f"input_{mode}.yaml"
        output_basedir = "myna_output"
        input_file_configured = os.path.join(
            output_basedir, f"input_{mode}_{now_str_id}.yaml"
        )
        os.makedirs(output_basedir, exist_ok=True)

        # Get configurable key words
        config_file = "config.yaml"
        with open(config_file, "r") as f:
            config_dict = yaml.safe_load(f)

        # Set case-specific configurable key words
        config_dict["3DTHESIS_RESOLUTION"] = resolution
        config_dict["MYNA_INPUT_FILE"] = os.path.basename(input_file_configured)

        # Update key words
        marker = str(config_dict["MARKER"])
        with open(input_file, "r") as f:
            input_lines = f.readlines()
        for i in range(len(input_lines)):
            for key in config_dict.keys():
                if key != "MARKER":
                    old = marker + key + marker
                    new = str(config_dict[key])
                    old_line = input_lines[i]
                    new_line = input_lines[i].replace(old, new)
                    input_lines[i] = new_line
                    if old_line == new_line:
                        print(key)
                        print("\t" + old + " --> " + new)
                        print("\told: " + old_line)
                        print("\tnew: " + new_line)

        with open(input_file_configured, "w") as f:
            f.writelines(input_lines)

        # Read and update input dictionary
        output_dir = os.path.basename(build_path).replace(" ", "_") + f"_{now_str_id}"
        with open(input_file_configured, "r") as f:
            input_dict = yaml.safe_load(f)
        input_dict["data"] = {}
        input_dict["data"]["build"] = {}
        input_dict["data"]["build"]["name"] = output_dir
        input_dict["data"]["build"]["path"] = build_path
        input_dict["data"]["build"]["parts"] = {}
        for part in exported_parts:
            input_dict["data"]["build"]["parts"][part] = {"layers": layers}

        # Export updated input dictionary
        with open(input_file_configured, "w") as f:
            yaml.dump(input_dict, f, default_flow_style=False)

    # Set working directory to the peregrine_launcher interface output directory
    # to run all myna scripts
    with working_directory(os.path.join(peregrine_launcher_path, output_basedir)):
        # Construct myna_config command
        input_file_configured = os.path.basename(input_file_configured)
        cmd = f"myna_config --input {input_file_configured}"
        p = subprocess.run(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        out = p.stdout.decode()

        # Parse output
        lines.append(f"{cmd=}\n\n")
        for line in out.split("\r\n"):
            print(line)
            lines.append(line + "\n")
        lines.append("\n")

        # Construct myna_run command
        cmd = f"myna_run --input {input_file_configured}"
        p = subprocess.run(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        out = p.stdout.decode()

        # Parse output
        lines.append(f"{cmd=}\n\n")
        for line in out.split("\r\n"):
            print(line)
            lines.append(line + "\n")
        lines.append("\n")

        # Get yyyy-mm-dd_hh-mm format for the current time
        now = datetime.datetime.now()
        now_str_pretty = now.strftime("%Y-%m-%d %H:%M:%S")

        # Add time to log file
        lines.append(f"\nSimulation completed at {now_str_pretty}\n")

        # Write log file
        with open(f"launch_from_peregrine_{now_str_id}.log", "w") as f:
            f.writelines(lines)
