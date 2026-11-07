# File: main.py
# Run command:
#   uvicorn main:app --host 0.0.0.0 --port 8000 --reload

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from core.bridge import EngineExecutionError, run_engine
except ImportError:
    EngineExecutionError = RuntimeError  # type: ignore[misc,assignment]
    run_engine = None


PROJECT_ROOT = Path(__file__).resolve().parent
ENGINE_BINARY = PROJECT_ROOT / "engine"
MODULES_DIR = PROJECT_ROOT / "modules"


class ProcessRequest(BaseModel):
    """Request schema for the POST /process endpoint."""

    mode: str = Field(default="sort_stats", description="Algorithm or track mode identifier.")
    size: int = Field(
        default=100_000,
        ge=1,
        le=50_000_000,
        description="Dataset or simulation batch size passed to the engine.",
    )
    seed: int = Field(default=42, ge=0, description="Deterministic random number generator seed.")
    threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Optional decision threshold parameter.",
    )
    intensity: int = Field(
        default=65,
        ge=1,
        le=100,
        description="Optional compute intensity level.",
    )
    runner: str = Field(
        default="cpp",
        pattern="^(cpp|python_module|auto)$",
        description="Target runner: 'cpp' (./engine), 'python_module' (modules/<script>.py), or 'auto'.",
    )
    module_name: Optional[str] = Field(
        default=None,
        description="Optional Python script name inside modules/ (e.g., 'worker.py' or 'worker').",
    )
    timeout_seconds: float = Field(
        default=10.0,
        gt=0.1,
        le=120.0,
        description="Subprocess execution timeout in seconds.",
    )
    data: Optional[Union[List[Any], Dict[str, Any]]] = Field(
        default=None,
        description="Optional custom payload data passed to Python module workers.",
    )


class ProcessResponse(BaseModel):
    """Structured JSON response returned by POST /process."""

    status: str
    execution_time_ms: float
    results: Dict[str, Any]


def _run_python_module(req: ProcessRequest) -> Dict[str, Any]:
    """Execute a Python worker script inside modules/ and parse its JSON stdout."""
    script_stem = (req.module_name or req.mode).removesuffix(".py")
    # Prevent path traversal outside MODULES_DIR
    safe_name = Path(script_stem).name + ".py"
    script_path = (MODULES_DIR / safe_name).resolve()

    if script_path.parent != MODULES_DIR.resolve() or not script_path.is_file():
        raise FileNotFoundError(f"Python worker module not found at 'modules/{safe_name}'.")

    cmd = [
        sys.executable,
        str(script_path),
        "--size",
        str(req.size),
        "--seed",
        str(req.seed),
        "--mode",
        req.mode,
        "--threshold",
        str(req.threshold),
        "--intensity",
        str(req.intensity),
    ]

    stdin_payload = json.dumps(req.data) if req.data is not None else None

    completed = subprocess.run(
        cmd,
        input=stdin_payload,
        capture_output=True,
        text=True,
        timeout=req.timeout_seconds,
        check=False,
        shell=False,
    )

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "Unknown module error"
        raise RuntimeError(f"Module 'modules/{safe_name}' exited with code {completed.returncode}: {detail}")

    stdout_text = completed.stdout.strip()
    if not stdout_text:
        raise RuntimeError(f"Module 'modules/{safe_name}' produced empty stdout.")

    try:
        parsed = json.loads(stdout_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON from 'modules/{safe_name}': {exc.msg}") from exc

    return parsed if isinstance(parsed, dict) else {"output": parsed}


def _run_cpp_binary(req: ProcessRequest) -> Dict[str, Any]:
    """Execute the compiled ./engine binary via core.bridge or direct subprocess."""
    cli_args: List[Union[str, int, float]] = [
        "--size",
        req.size,
        "--seed",
        req.seed,
        "--mode",
        req.mode,
    ]

    if run_engine is not None:
        return run_engine(
            cli_args,
            executable_path=ENGINE_BINARY,
            timeout_seconds=req.timeout_seconds,
        )

    if not ENGINE_BINARY.is_file():
        raise FileNotFoundError(
            f"Compiled C++ binary not found at '{ENGINE_BINARY}'. "
            "Compile with: g++ -O3 -std=c++17 -Wall -Wextra core/engine.cpp -o engine"
        )

    completed = subprocess.run(
        [str(ENGINE_BINARY), *[str(a) for a in cli_args]],
        capture_output=True,
        text=True,
        timeout=req.timeout_seconds,
        check=False,
        shell=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "C++ engine error"
        raise RuntimeError(f"C++ binary exited with code {completed.returncode}: {detail}")

    return json.loads(completed.stdout.strip())


def execute_worker(req: ProcessRequest) -> Dict[str, Any]:
    """Dispatch parameters to the local C++ binary or a Python script in modules/."""
    if req.runner == "python_module":
        output = _run_python_module(req)
        output["runner_used"] = "python_module"
        return output

    if req.runner == "cpp":
        output = _run_cpp_binary(req)
        output["runner_used"] = "cpp_engine"
        return output

    # runner == "auto": prefer C++ binary if present, otherwise try modules/ script
    if ENGINE_BINARY.is_file():
        output = _run_cpp_binary(req)
        output["runner_used"] = "cpp_engine"
        return output

    output = _run_python_module(req)
    output["runner_used"] = "python_module"
    return output


app = FastAPI(
    title="Hackathon C++ / Python Engine API",
    description="Lightweight FastAPI backend serving the C++ ./engine binary and modules/ workers.",
    version="1.0.0",
)

# Enable permissive CORS so any web or local frontend can call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> Dict[str, Any]:
    """Return service readiness and binary availability."""
    return {
        "status": "ok",
        "engine_binary_present": ENGINE_BINARY.is_file(),
        "modules_dir_present": MODULES_DIR.is_dir(),
    }


@app.post("/process", response_model=ProcessResponse)
def process_payload(request: ProcessRequest) -> ProcessResponse:
    """Run the C++ engine or a Python module worker with the supplied parameters."""
    wall_start = time.perf_counter()
    try:
        worker_results = execute_worker(request)
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(
            status_code=504,
            detail=f"Worker execution timed out after {request.timeout_seconds}s: {exc}",
        ) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (EngineExecutionError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    wall_elapsed_ms = round((time.perf_counter() - wall_start) * 1000.0, 3)

    # Prefer high-resolution internal engine timing if reported, otherwise wall-clock time
    engine_ms = (
        worker_results.get("metrics", {}).get("execution_time_ms")
        if isinstance(worker_results.get("metrics"), dict)
        else None
    )
    reported_time_ms = float(engine_ms) if engine_ms is not None else wall_elapsed_ms

    return ProcessResponse(
        status="ok",
        execution_time_ms=round(reported_time_ms, 3),
        results={
            **worker_results,
            "request_echo": {
                "mode": request.mode,
                "size": request.size,
                "seed": request.seed,
                "threshold": request.threshold,
                "intensity": request.intensity,
                "runner": request.runner,
            },
            "wall_clock_time_ms": wall_elapsed_ms,
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)