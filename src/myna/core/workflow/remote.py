#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Launch, inspect, and retrieve interactive SSH Myna workflows."""

import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import shlex
import shutil
import subprocess
import tempfile
import time
import uuid
import zipfile

from myna.core.workflow import config
from myna.core.workflow.load_input import load_input, write_input


_REMOTE_WORKER = r"""
import json
from pathlib import Path
import subprocess
import sys
import traceback
import zipfile

mode, run_dir_text, archive_text, input_name, command, step, download, workspace, launch_input = sys.argv[1:]
run_dir, archive = Path(run_dir_text), Path(archive_text)
status_path = run_dir / "myna_remote_status.json"

def write_status(state, **extra):
    temporary = status_path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"state": state, **extra}, indent=2), encoding="utf-8")
    temporary.replace(status_path)

def load_settings(path):
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    import yaml
    return yaml.safe_load(path.read_text(encoding="utf-8"))

def write_settings(settings, path):
    if path.suffix.lower() == ".json":
        path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    else:
        import yaml
        path.write_text(yaml.safe_dump(settings, sort_keys=False), encoding="utf-8")

try:
    write_status("running")
    original_workspace = None
    if mode == "local":
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(run_dir)
        input_path = run_dir / input_name
    else:
        settings = json.loads(Path(launch_input).read_text(encoding="utf-8"))
        input_path = run_dir / input_name
        input_path.parent.mkdir(parents=True, exist_ok=True)
        myna_settings = settings.setdefault("myna", {})
        original_workspace = myna_settings.get("workspace")
        if workspace:
            myna_settings["workspace"] = workspace
        write_settings(settings, input_path)
        subprocess.run([command, "config", "--input", str(input_path)], cwd=run_dir, check=True)

    settings = load_settings(input_path)
    myna_settings = settings.setdefault("myna", {})
    if mode == "local":
        original_workspace = myna_settings.get("workspace")
    if workspace and mode == "local":
        myna_settings["workspace"] = workspace
        write_settings(settings, input_path)
    command_args = [command, "run", "--input", str(input_path)]
    if step:
        command_args.extend(["--step", step])
    subprocess.run(command_args, cwd=run_dir, check=True)

    if workspace:
        settings = load_settings(input_path)
        if original_workspace is None:
            settings.setdefault("myna", {}).pop("workspace", None)
        else:
            settings.setdefault("myna", {})["workspace"] = original_workspace
        write_settings(settings, input_path)

    result_archive = run_dir / "myna_remote_results.zip"
    with zipfile.ZipFile(result_archive, "w", zipfile.ZIP_DEFLATED) as result:
        if download == "all":
            paths = [path for path in run_dir.rglob("*") if path != result_archive]
        else:
            settings, paths = load_settings(input_path), [input_path]
            for step_paths in settings.get("data", {}).get("output_paths", {}).values():
                for output in step_paths:
                    path = Path(output)
                    if not path.is_absolute(): path = input_path.parent / path
                    if path.exists(): paths.append(path)
        for path in paths:
            if path.is_file(): result.write(path, path.relative_to(run_dir))
    write_status("succeeded", result_archive=str(result_archive))
except BaseException as error:
    write_status("failed", error=repr(error), traceback=traceback.format_exc())
    raise
"""

_REMOTE_WRITE_JSON = (
    "import sys; from pathlib import Path; path = Path(sys.argv[1]); "
    "path.parent.mkdir(parents=True, exist_ok=True); "
    "path.write_text(sys.stdin.read(), encoding='utf-8')"
)


def parse(parser):
    """Parse remote launch, check, and update commands."""

    parser.add_argument("--input", default="input.yaml", type=str)
    parser.add_argument("--step", type=str)
    parser.add_argument("--tracker", type=str)
    parser.add_argument("--wait", action="store_true")
    args = parser.parse_args()
    actions = [value for value in args.type if value != "remote"]
    if len(actions) > 1 or any(value not in ("check", "update") for value in actions):
        parser.error('remote accepts at most one action: "check" or "update"')
    action = actions[0] if actions else "launch"
    if action == "launch":
        launch(args.input, args.step, args.wait)
    elif action == "check":
        check(args.input, args.tracker)
    else:
        update(args.input, args.tracker)


def _get_compute_settings(settings):
    compute = settings.get("myna", {}).get("compute")
    if not isinstance(compute, dict):
        raise ValueError('Remote execution requires a "myna.compute" dictionary.')
    required = ("host", "workdir", "command", "data_location")
    missing = [key for key in required if not isinstance(compute.get(key), str)]
    if missing:
        raise ValueError(
            "myna.compute requires string values for: " + ", ".join(missing)
        )
    if not PurePosixPath(compute["workdir"]).is_absolute():
        raise ValueError("myna.compute.workdir must be an absolute POSIX path.")
    if not PurePosixPath(compute["command"]).is_absolute():
        raise ValueError("myna.compute.command must be an absolute POSIX path.")
    if compute["data_location"] not in ("local", "remote"):
        raise ValueError('myna.compute.data_location must be "local" or "remote".')
    workspace = compute.get("workspace")
    if workspace is not None and (
        not isinstance(workspace, str) or not PurePosixPath(workspace).is_absolute()
    ):
        raise ValueError("myna.compute.workspace must be an absolute POSIX path.")
    download = compute.get("download", "all")
    if download not in ("all", "outputs"):
        raise ValueError('myna.compute.download must be "all" or "outputs".')
    return {
        "host": compute["host"],
        "workdir": compute["workdir"].rstrip("/"),
        "command": compute["command"],
        "python": str(PurePosixPath(compute["command"]).with_name("python")),
        "data_location": compute["data_location"],
        "workspace": workspace,
        "download": download,
    }


def _walk_file_local_paths(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "file_local" and isinstance(child, str):
                yield child
            else:
                yield from _walk_file_local_paths(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_file_local_paths(child)


def _input_runtime_paths(settings, input_path):
    paths = {input_path}
    workspace = settings.get("myna", {}).get("workspace")
    if isinstance(workspace, str):
        paths.add(Path(workspace))
    paths.update(
        Path(name) for name in _walk_file_local_paths(settings.get("data", {}))
    )
    for step in settings.get("steps", []):
        for step_settings in step.values() if isinstance(step, dict) else []:
            for operation in ("configure", "execute", "postprocess"):
                values = step_settings.get(operation, {})
                if isinstance(values, dict):
                    for key in ("docker-config", "docker_config"):
                        if isinstance(values.get(key), str):
                            paths.add(Path(values[key]))
    return {path.resolve(strict=False) for path in paths if path.exists()}


def _archive_root(paths):
    common = Path(os.path.commonpath([os.fspath(path) for path in paths]))
    return common if common.is_dir() else common.parent


def _write_bundle(bundle_path, paths, root):
    with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as bundle:
        written = set()
        for path in sorted(paths):
            for candidate in path.rglob("*") if path.is_dir() else (path,):
                if candidate.is_file() and candidate not in written:
                    bundle.write(candidate, candidate.relative_to(root))
                    written.add(candidate)


def _extract_bundle(bundle_path, destination):
    destination = destination.resolve()
    with zipfile.ZipFile(bundle_path) as bundle:
        for member in bundle.infolist():
            if (
                not (destination / member.filename)
                .resolve()
                .is_relative_to(destination)
            ):
                raise ValueError(
                    f"Remote archive contains unsafe path: {member.filename}"
                )
        bundle.extractall(destination)


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _ssh(host, command, input_text=None, capture_output=False):
    return subprocess.run(
        ["ssh", host, command],
        input=input_text,
        text=input_text is not None or capture_output,
        capture_output=capture_output,
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


def _tracker_directory(input_path):
    return input_path.parent / ".myna" / "remote"


def _find_tracker(input_path):
    candidates = []
    for path in _tracker_directory(input_path).glob("*.json"):
        tracker = _read_json(path)
        if tracker.get("input_file") == os.fspath(input_path) and not tracker.get(
            "retrieved"
        ):
            candidates.append((tracker.get("created_at", ""), path))
    if not candidates:
        raise FileNotFoundError("No unfinished remote tracker found for this input.")
    return max(candidates)[1]


def _load_tracker(input_file, tracker_file):
    path = (
        Path(tracker_file).expanduser().resolve()
        if tracker_file
        else _find_tracker(Path(input_file).expanduser().resolve())
    )
    return path, _read_json(path)


def _stage_local_snapshot(input_path, settings, temporary_dir):
    source_paths = _input_runtime_paths(settings, input_path)
    source_root = _archive_root(source_paths)
    seed, stage_root = temporary_dir / "seed.zip", temporary_dir / "stage"
    _write_bundle(seed, source_paths, source_root)
    _extract_bundle(seed, stage_root)
    staged_input = stage_root / input_path.relative_to(source_root)
    _rebase_snapshot_runtime_paths(settings, source_root, stage_root)
    write_input(settings, staged_input, relative_paths=True)
    config.config(os.fspath(staged_input))
    configured = load_input(staged_input)
    paths = _input_runtime_paths(configured, staged_input)
    resources = staged_input.parent / "myna_resources"
    if resources.exists():
        paths.add(resources)
    for values in configured.get("data", {}).get("output_paths", {}).values():
        paths.update(
            Path(value).parent for value in values if Path(value).parent.exists()
        )
    bundle = temporary_dir / "myna_remote_bundle.zip"
    _write_bundle(bundle, paths, stage_root)
    return bundle, staged_input.relative_to(stage_root)


def _rebase_snapshot_runtime_paths(settings, source_root, stage_root):
    """Point copied runtime files at their matching path in a job snapshot."""

    def rebase(value):
        path = Path(value)
        if path.is_absolute() and path.is_relative_to(source_root):
            return os.fspath(stage_root / path.relative_to(source_root))
        return value

    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "file_local" and isinstance(child, str):
                    value[key] = rebase(child)
                else:
                    walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    myna_settings = settings.get("myna", {})
    if isinstance(myna_settings.get("workspace"), str):
        myna_settings["workspace"] = rebase(myna_settings["workspace"])
    walk(settings.get("data", {}))
    for paths in settings.get("data", {}).get("output_paths", {}).values():
        if isinstance(paths, list):
            for index, path in enumerate(paths):
                if isinstance(path, str):
                    paths[index] = rebase(path)
    for step in settings.get("steps", []):
        for step_settings in step.values() if isinstance(step, dict) else []:
            for operation in ("configure", "execute", "postprocess"):
                values = step_settings.get(operation, {})
                if isinstance(values, dict):
                    for key in ("docker-config", "docker_config"):
                        if isinstance(values.get(key), str):
                            values[key] = rebase(values[key])


def _worker_command(compute, tracker):
    return shlex.join(
        [
            compute["python"],
            "-c",
            _REMOTE_WORKER,
            compute["data_location"],
            tracker["remote_dir"],
            tracker["remote_bundle"],
            tracker["input_member"],
            compute["command"],
            tracker["step"] or "",
            compute["download"],
            compute["workspace"] or "",
            tracker["remote_launch_input"],
        ]
    )


def launch(input_file, step=None, wait=False):
    input_path = Path(input_file).expanduser().resolve()
    settings = load_input(input_path)
    compute = _get_compute_settings(settings)
    run_id, run_name = uuid.uuid4().hex, None
    run_name = f"myna-{input_path.stem}-{run_id}"
    remote_dir = posixpath.join(compute["workdir"], run_name)
    tracker_path = _tracker_directory(input_path) / f"{run_id}.json"
    tracker = {
        "uuid": run_id,
        "input_file": os.fspath(input_path),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": compute["host"],
        "remote_dir": remote_dir,
        "remote_bundle": posixpath.join(remote_dir, "myna_remote_bundle.zip"),
        "remote_launch_input": posixpath.join(remote_dir, "myna_remote_input.json"),
        "remote_status": posixpath.join(remote_dir, "myna_remote_status.json"),
        "remote_results": posixpath.join(remote_dir, "myna_remote_results.zip"),
        "data_location": compute["data_location"],
        "download": compute["download"],
        "step": step,
        "result_dir": os.fspath(input_path.parent / "myna_remote" / run_id),
        "state": "launching",
        "retrieved": False,
    }
    _write_json(tracker_path, tracker)
    try:
        with tempfile.TemporaryDirectory(prefix="myna-remote-") as temporary:
            temporary_dir = Path(temporary)
            _ssh(compute["host"], shlex.join(["mkdir", "-p", remote_dir]))
            if compute["data_location"] == "local":
                bundle, input_member = _stage_local_snapshot(
                    input_path, settings, temporary_dir
                )
                tracker["input_member"] = os.fspath(input_member)
                _scp_to(compute["host"], bundle, tracker["remote_bundle"])
            else:
                tracker["input_member"] = input_path.name
                _ssh(
                    compute["host"],
                    shlex.join(
                        [
                            compute["python"],
                            "-c",
                            _REMOTE_WRITE_JSON,
                            tracker["remote_launch_input"],
                        ]
                    ),
                    json.dumps(settings),
                )
            process = _ssh(
                compute["host"],
                f"cd {shlex.quote(remote_dir)} && nohup {_worker_command(compute, tracker)} > worker.stdout.log 2> worker.stderr.log < /dev/null & echo $!",
                capture_output=True,
            )
            tracker.update({"pid": process.stdout.strip(), "state": "launched"})
            _write_json(tracker_path, tracker)
    except Exception:
        tracker["state"] = "launch_failed"
        _write_json(tracker_path, tracker)
        raise
    print(f"Remote Myna tracker: {tracker_path}")
    print(f"Remote Myna run directory: {compute['host']}:{remote_dir}")
    return _wait_and_update(tracker_path, tracker) if wait else tracker_path


def check(input_file="input.yaml", tracker_file=None):
    tracker_path, tracker = _load_tracker(input_file, tracker_file)
    try:
        result = _ssh(
            tracker["host"],
            shlex.join(["cat", tracker["remote_status"]]),
            capture_output=True,
        )
        status = json.loads(result.stdout)
    except subprocess.CalledProcessError:
        print(
            f"Remote Myna run status unavailable: {tracker['host']}:{tracker['remote_dir']}"
        )
        return tracker
    tracker.update({"state": status["state"], "remote_status_data": status})
    _write_json(tracker_path, tracker)
    print(f"Remote Myna run {tracker['uuid']}: {status['state']}")
    if status["state"] == "failed":
        print(
            f"Remote logs: {tracker['host']}:{tracker['remote_dir']}/worker.stdout.log"
        )
        print(
            f"Remote logs: {tracker['host']}:{tracker['remote_dir']}/worker.stderr.log"
        )
    return tracker


def _publish_results(tracker_path, tracker):
    result_dir = Path(tracker["result_dir"])
    if result_dir.exists():
        tracker["retrieved"] = True
        _write_json(tracker_path, tracker)
        return tracker
    result_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f".{tracker['uuid']}-", dir=result_dir.parent
    ) as temporary:
        archive, extracted = (
            Path(temporary) / "results.zip",
            Path(temporary) / "extracted",
        )
        extracted.mkdir()
        _scp_from(tracker["host"], tracker["remote_results"], archive)
        _extract_bundle(archive, extracted)
        shutil.move(os.fspath(extracted), os.fspath(result_dir))
    tracker.update(
        {
            "retrieved": True,
            "snapshot_input": os.fspath(result_dir / tracker["input_member"]),
        }
    )
    _write_json(tracker_path, tracker)
    print(f"Remote Myna results: {result_dir}")
    print(f"Configured input snapshot: {tracker['snapshot_input']}")
    return tracker


def update(input_file="input.yaml", tracker_file=None):
    tracker_path, tracker = _load_tracker(input_file, tracker_file)
    if tracker.get("retrieved"):
        print(f"Remote Myna results already retrieved: {tracker['result_dir']}")
        return tracker
    tracker = check(input_file, tracker_path)
    if tracker.get("state") == "failed":
        return tracker
    if tracker.get("state") != "succeeded":
        print("Remote Myna results are not ready for retrieval.")
        return tracker
    tracker = _publish_results(tracker_path, tracker)
    if tracker["download"] == "all":
        _ssh(tracker["host"], shlex.join(["rm", "-rf", tracker["remote_dir"]]))
        tracker["remote_cleaned"] = True
        _write_json(tracker_path, tracker)
        print(
            f"Remote Myna run directory cleaned: {tracker['host']}:{tracker['remote_dir']}"
        )
    else:
        print(
            f"Remote Myna run directory retained: {tracker['host']}:{tracker['remote_dir']}"
        )
    return tracker


def _wait_and_update(tracker_path, tracker):
    while True:
        current = check(tracker["input_file"], tracker_path)
        if current.get("state") in ("succeeded", "failed"):
            return update(tracker["input_file"], tracker_path)
        time.sleep(5)
