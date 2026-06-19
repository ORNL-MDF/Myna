"""Check whether the local shell is ready for Myna development.

The check is designed for humans and coding agents. It uses only the Python standard
library so it can run before the project environment has been synced.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MIN_PYTHON = (3, 10)
COMMAND_TIMEOUT_SECONDS = 120
DEV_TOOL_COMMANDS = [
    ["pytest", "--version"],
    ["ruff", "--version"],
    ["mkdocs", "--version"],
    ["pre-commit", "--version"],
]


def print_status(kind: str, message: str) -> None:
    print(f"[{kind}] {message}")


def format_env_var_examples(name: str, value: str) -> str:
    return (
        f"  POSIX shell: export {name}={value}\n  PowerShell:  $env:{name} = '{value}'"
    )


def find_common_uv_candidates() -> list[Path]:
    home = Path.home()
    candidates = [
        home / ".local" / "bin" / "uv",
        home / ".cargo" / "bin" / "uv",
        home / "snap" / "code" / "current" / ".local" / "bin" / "uv",
        Path("/opt/homebrew/bin/uv"),
        Path("/usr/local/bin/uv"),
    ]
    uv_env = os.environ.get("UV")
    if uv_env:
        candidates.insert(0, Path(uv_env))
    return [path for path in candidates if path.exists()]


def check_current_python(errors: list[str]) -> None:
    version = sys.version_info
    if version < MIN_PYTHON:
        errors.append(
            "Current Python is "
            f"{version.major}.{version.minor}.{version.micro}; "
            f"Myna development requires Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+."
        )
        return
    print_status(
        "ok",
        f"current Python is {version.major}.{version.minor}.{version.micro}",
    )


def check_uv_on_path(errors: list[str], warnings: list[str]) -> str | None:
    uv = shutil.which("uv")
    if uv:
        print_status("ok", f"uv found on PATH: {uv}")
        return uv

    candidates = find_common_uv_candidates()
    if candidates:
        paths = "\n".join(f"  - {path}" for path in candidates)
        path_dirs = os.pathsep.join(str(path.parent) for path in candidates)
        errors.append(
            "uv was found in a common install location, but it is not on PATH:\n"
            f"{paths}\n"
            "Add the containing directory to PATH. For example, prepend:\n"
            f"  {path_dirs}\n"
            f"using your shell's PATH syntax."
        )
    else:
        errors.append(
            "uv is not installed or is not discoverable. Install uv, then make sure "
            "the uv executable is on PATH. See "
            "https://docs.astral.sh/uv/getting-started/installation/."
        )

    warnings.append(
        "Non-interactive agent shells may not load the same startup files as an "
        "interactive terminal. Verify PATH in the shell that will run validations."
    )
    return None


def directory_is_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path):
            pass
    except OSError:
        return False
    return True


def check_cache_dir(
    env_var: str,
    default_path: Path,
    fallback_path: str,
    errors: list[str],
) -> None:
    path = Path(os.environ.get(env_var, default_path)).expanduser()
    if directory_is_writable(path):
        print_status("ok", f"{env_var or default_path} cache is writable: {path}")
        return

    errors.append(
        f"{path} is not writable. Set a writable cache directory before running "
        f"development commands, for example:\n"
        f"{format_env_var_examples(env_var, fallback_path)}"
    )


def run_command(
    command: list[str],
    errors: list[str],
    *,
    label: str,
    timeout: int = COMMAND_TIMEOUT_SECONDS,
) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        errors.append(f"{label} failed because the command was not found: {exc}")
        return ""
    except subprocess.TimeoutExpired:
        errors.append(f"{label} timed out after {timeout} seconds.")
        return ""

    output = "\n".join(
        part.strip() for part in [result.stdout, result.stderr] if part.strip()
    )
    if result.returncode != 0:
        errors.append(
            f"{label} failed with exit code {result.returncode}:\n{output or '(no output)'}"
        )
        return output

    print_status("ok", f"{label}: {output.splitlines()[0] if output else 'passed'}")
    return output


def command_failed_because_tool_missing(output: str) -> bool:
    missing_tool_markers = [
        "No such file or directory",
        "Failed to spawn",
        "command not found",
        "ModuleNotFoundError",
    ]
    return any(marker in output for marker in missing_tool_markers)


def check_project_commands(uv: str, errors: list[str], warnings: list[str]) -> None:
    run_command([uv, "--version"], errors, label="uv version")
    run_command([uv, "lock", "--check"], errors, label="uv lock --check")
    python_output = run_command(
        [
            uv,
            "run",
            "--frozen",
            "--no-sync",
            "python",
            "-c",
            "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')",
        ],
        errors,
        label="project Python",
    )
    if python_output and not python_output.startswith("3.10."):
        warnings.append(
            "CI builds docs with Python 3.10. If API-doc generation fails locally, "
            "sync a Python 3.10 environment with "
            "`uv sync --frozen --extra dev --python 3.10`."
        )

    missing_dev_tools = []
    for tool_command in DEV_TOOL_COMMANDS:
        before_error_count = len(errors)
        output = run_command(
            [uv, "run", "--frozen", "--no-sync", *tool_command],
            errors,
            label=f"uv run {' '.join(tool_command)}",
        )
        if len(errors) > before_error_count and command_failed_because_tool_missing(
            output
        ):
            missing_dev_tools.append(tool_command[0])

    if missing_dev_tools:
        errors.append(
            "Development tools are not installed in the project environment: "
            + ", ".join(sorted(set(missing_dev_tools)))
            + ". From a fresh clone, run:\n"
            "  uv sync --frozen --extra dev\n"
            "If you need CI docs parity, use:\n"
            "  uv sync --frozen --extra dev --python 3.10"
        )


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    check_current_python(errors)
    uv = check_uv_on_path(errors, warnings)
    check_cache_dir(
        "UV_CACHE_DIR", Path.home() / ".cache" / "uv", "/tmp/uv-cache", errors
    )
    check_cache_dir(
        "PRE_COMMIT_HOME",
        Path.home() / ".cache" / "pre-commit",
        "/tmp/pre-commit-cache",
        errors,
    )

    if uv is not None:
        check_project_commands(uv, errors, warnings)

    for warning in warnings:
        print_status("warn", warning)

    if errors:
        print("\nDevelopment tool check failed. Fix the following:")
        for index, error in enumerate(errors, start=1):
            print(f"\n{index}. {error}")
        return 1

    print("\nDevelopment tool check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
