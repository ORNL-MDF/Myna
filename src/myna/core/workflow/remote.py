#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Run an interactive Myna workflow on an SSH-accessible remote host."""

import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import shlex
import subprocess
import tempfile
import uuid
import zipfile

from myna.core.workflow import config
from myna.core.workflow.load_input import load_input


_REMOTE_BOOTSTRAP = r"""
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

mode, run_dir_text, archive_text, input_name, command, step, download = sys.argv[1:]
run_dir = Path(run_dir_text)
archive = Path(archive_text)
run_dir.mkdir(parents=True, exist_ok=True)

if mode == "local":
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(run_dir)
    input_path = run_dir / input_name
    command_args = [command, "run", "--input", str(input_path)]
else:
    settings = json.load(sys.stdin)
    input_path = run_dir / input_name
    if input_path.suffix.lower() == ".json":
        input_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    else:
        import yaml
        input_path.write_text(yaml.safe_dump(settings, sort_keys=False), encoding="utf-8")
    subprocess.run(
        [command, "config", "--input", str(input_path)], cwd=run_dir, check=True
    )
    command_args = [command, "run", "--input", str(input_path)]

if step:
    command_args.extend(["--step", step])
subprocess.run(command_args, cwd=run_dir, check=True)

settings = json.loads(input_path.read_text(encoding="utf-8")) if input_path.suffix.lower() == ".json" else None
if settings is None:
    import yaml
    settings = yaml.safe_load(input_path.read_text(encoding="utf-8"))

result_archive = run_dir / "myna_remote_results.zip"
with zipfile.ZipFile(result_archive, "w", zipfile.ZIP_DEFLATED) as result:
    if download == "all":
        paths = [path for path in run_dir.rglob("*") if path != result_archive]
    else:
        paths = [input_path]
        for step_paths in settings.get("data", {}).get("output_paths", {}).values():
            for output in step_paths:
                path = Path(output)
                if not path.is_absolute():
                    path = input_path.parent / path
                if path.exists():
                    paths.append(path)
    for path in paths:
        if path.is_file():
            result.write(path, path.relative_to(run_dir))
"""


def parse(parser):
    """Register and parse the ``myna remote`` command arguments."""

    parser.add_argument("--input", default="input.yaml", type=str)
    parser.add_argument("--step", type=str)
    args = parser.parse_args()
    remote(args.input, args.step)


def _get_compute_settings(settings):
    """Validate and normalize the opt-in remote compute settings."""

    compute = settings.get("myna", {}).get("compute")
    if not isinstance(compute, dict):
        raise ValueError('Remote execution requires a "myna.compute" dictionary.')

    required = ("host", "workdir", "command", "data_location")
    missing = [key for key in required if not isinstance(compute.get(key), str)]
    if missing:
        raise ValueError(
            "myna.compute requires string values for: " + ", ".join(missing)
        )

    workdir = compute["workdir"]
    command = compute["command"]
    if not PurePosixPath(workdir).is_absolute():
        raise ValueError("myna.compute.workdir must be an absolute POSIX path.")
    if not PurePosixPath(command).is_absolute():
        raise ValueError("myna.compute.command must be an absolute POSIX path.")
    if compute["data_location"] not in ("local", "remote"):
        raise ValueError('myna.compute.data_location must be "local" or "remote".')

    download = compute.get("download", "all")
    if download not in ("all", "outputs"):
        raise ValueError('myna.compute.download must be "all" or "outputs".')

    return {
        "host": compute["host"],
        "workdir": workdir.rstrip("/"),
        "command": command,
        "python": str(PurePosixPath(command).with_name("python")),
        "data_location": compute["data_location"],
        "download": download,
    }


def _walk_file_local_paths(value):
    """Yield data-file paths from a configured Myna settings structure."""

    if isinstance(value, dict):
        for key, child in value.items():
            if key == "file_local" and isinstance(child, str):
                yield child
            else:
                yield from _walk_file_local_paths(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_file_local_paths(child)


def _runtime_paths(settings, input_path):
    """Return locally required files and directories for a staged run."""

    paths = {input_path}
    workspace = settings.get("myna", {}).get("workspace")
    if isinstance(workspace, str):
        paths.add(Path(workspace))
    for filename in _walk_file_local_paths(settings.get("data", {})):
        paths.add(Path(filename))
    for step in settings.get("steps", []):
        for step_settings in step.values() if isinstance(step, dict) else []:
            for operation in ("configure", "execute", "postprocess"):
                operation_settings = step_settings.get(operation, {})
                if isinstance(operation_settings, dict):
                    for key in ("docker-config", "docker_config"):
                        if isinstance(operation_settings.get(key), str):
                            paths.add(Path(operation_settings[key]))
    for directory in (input_path.parent / "myna_resources",):
        if directory.exists():
            paths.add(directory)
    for step_paths in settings.get("data", {}).get("output_paths", {}).values():
        for output in step_paths:
            paths.add(Path(output).parent)
    return {path.resolve(strict=False) for path in paths if path.exists()}


def _archive_root(paths):
    """Find a common local root while retaining only explicitly selected paths."""

    common = os.path.commonpath([os.fspath(path) for path in paths])
    return Path(common if Path(common).is_dir() else Path(common).parent)


def _write_bundle(bundle_path, paths, root):
    """Create a ZIP containing selected files while preserving their layout."""

    with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as bundle:
        written = set()
        for path in sorted(paths):
            candidates = path.rglob("*") if path.is_dir() else (path,)
            for candidate in candidates:
                if not candidate.is_file() or candidate in written:
                    continue
                bundle.write(candidate, candidate.relative_to(root))
                written.add(candidate)


def _ssh(host, remote_command, input_text=None):
    """Run a command through SSH using the caller's normal SSH configuration."""

    return subprocess.run(
        ["ssh", host, remote_command],
        input=input_text,
        text=input_text is not None,
        check=True,
    )


def _scp_to(host, local_path, remote_path):
    subprocess.run(
        ["scp", os.fspath(local_path), f"{host}:{shlex.quote(remote_path)}"], check=True
    )


def _scp_from(host, remote_path, local_path):
    subprocess.run(
        ["scp", f"{host}:{shlex.quote(remote_path)}", os.fspath(local_path)], check=True
    )


def _remote_command(compute, run_dir, archive, input_name, step):
    args = [
        compute["python"],
        "-c",
        _REMOTE_BOOTSTRAP,
        compute["data_location"],
        run_dir,
        archive,
        input_name,
        compute["command"],
        step or "",
        compute["download"],
    ]
    return shlex.join(args)


def _extract_bundle(bundle_path, destination):
    """Extract a result ZIP after rejecting entries that escape its destination."""

    destination = destination.resolve()
    with zipfile.ZipFile(bundle_path) as bundle:
        for member in bundle.infolist():
            target = (destination / member.filename).resolve()
            if not target.is_relative_to(destination):
                raise ValueError(
                    f"Remote archive contains unsafe path: {member.filename}"
                )
        bundle.extractall(destination)


def remote(input_file, step=None):
    """Configure and run an interactive workflow on a remote host."""

    input_path = Path(input_file).expanduser().resolve()
    settings = load_input(input_path)
    compute = _get_compute_settings(settings)
    run_name = f"myna-{input_path.stem}-{uuid.uuid4().hex}"
    run_dir = posixpath.join(compute["workdir"], run_name)
    remote_bundle = posixpath.join(run_dir, "myna_remote_bundle.zip")
    remote_results = posixpath.join(run_dir, "myna_remote_results.zip")
    archive_root = input_path.parent

    print(f"Remote Myna run directory: {compute['host']}:{run_dir}")
    try:
        with tempfile.TemporaryDirectory(prefix="myna-remote-") as temporary_dir:
            temporary_dir = Path(temporary_dir)
            local_bundle = temporary_dir / "myna_remote_bundle.zip"
            local_results = temporary_dir / "myna_remote_results.zip"

            if compute["data_location"] == "local":
                config.config(os.fspath(input_path))
                settings = load_input(input_path)
                paths = _runtime_paths(settings, input_path)
                archive_root = _archive_root(paths)
                _write_bundle(local_bundle, paths, archive_root)
                _ssh(compute["host"], shlex.join(["mkdir", "-p", run_dir]))
                _scp_to(compute["host"], local_bundle, remote_bundle)

            input_name = os.fspath(input_path.relative_to(archive_root))
            command = _remote_command(compute, run_dir, remote_bundle, input_name, step)
            input_text = (
                json.dumps(settings) if compute["data_location"] == "remote" else None
            )
            _ssh(compute["host"], command, input_text)
            _scp_from(compute["host"], remote_results, local_results)
            _extract_bundle(local_results, archive_root)

        if compute["download"] == "all":
            _ssh(compute["host"], shlex.join(["rm", "-rf", run_dir]))
            print(f"Remote Myna run directory cleaned: {compute['host']}:{run_dir}")
        else:
            print(f"Remote Myna run directory retained: {compute['host']}:{run_dir}")
    except Exception:
        print(
            f"Remote Myna run directory retained after failure: {compute['host']}:{run_dir}"
        )
        raise
