# File: core/bridge.py
"""Subprocess bridge for invoking the compiled C++ ./engine executable."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Sequence, Union


class EngineExecutionError(RuntimeError):
    """Raised when the C++ engine fails, times out, or returns invalid JSON."""


DEFAULT_ENGINE_PATH = Path(__file__).resolve().parent.parent / "engine"


def run_engine(
    args: Sequence[Union[str, int, float]] = (),
    *,
    executable_path: Union[str, Path] = DEFAULT_ENGINE_PATH,
    timeout_seconds: float = 10.0,
) -> Dict[str, Any]:
    """Securely invoke the C++ engine executable and parse its JSON stdout.

    Args:
        args: Command-line arguments passed to the engine (e.g., ["--size", 100000]).
        executable_path: Path to the compiled `engine` binary (defaults to `./engine`).
        timeout_seconds: Maximum allowed execution time in seconds before aborting.

    Returns:
        Parsed JSON response from the C++ engine as a Python dictionary.

    Raises:
        FileNotFoundError: If the compiled engine binary does not exist.
        EngineExecutionError: If execution times out, exits non-zero, or emits invalid JSON.
    """
    binary = Path(executable_path).resolve()
    if not binary.is_file():
        raise FileNotFoundError(
            f"Compiled C++ binary not found at '{binary}'. "
            "Compile it first with: g++ -O3 -std=c++17 -Wall -Wextra core/engine.cpp -o engine"
        )

    cmd = [str(binary), *[str(arg) for arg in args]]

    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise EngineExecutionError(
            f"C++ engine timed out after {timeout_seconds:.2f}s (args={list(args)})."
        ) from exc
    except OSError as exc:
        raise EngineExecutionError(f"Failed to execute C++ binary '{binary}': {exc}") from exc

    stdout_text = completed.stdout.strip()
    stderr_text = completed.stderr.strip()

    if completed.returncode != 0:
        # Attempt to surface structured error message if the engine printed error JSON
        try:
            err_payload = json.loads(stdout_text) if stdout_text else {}
        except json.JSONDecodeError:
            err_payload = {}
        detail = err_payload.get("message") or stderr_text or stdout_text or "Unknown error"
        raise EngineExecutionError(
            f"C++ engine exited with code {completed.returncode}: {detail}"
        )

    if not stdout_text:
        raise EngineExecutionError("C++ engine returned empty stdout.")

    try:
        parsed: Dict[str, Any] = json.loads(stdout_text)
    except json.JSONDecodeError as exc:
        raise EngineExecutionError(
            f"Failed to parse JSON from C++ engine stdout: {exc.msg} (raw={stdout_text!r})"
        ) from exc

    if not isinstance(parsed, dict):
        raise EngineExecutionError(
            f"Expected JSON object from C++ engine, got {type(parsed).__name__}."
        )

    return parsed


if __name__ == "__main__":
    result = run_engine(["--size", 100000, "--seed", 42])
    print(json.dumps(result, indent=2))