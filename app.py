# File: app.py
# Run command:
#   streamlit run app.py

from __future__ import annotations

import io
import json
import math
import random
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

# Optional integration with core.bridge if compiled binary is present
try:
    from core.bridge import EngineExecutionError, run_engine
except ImportError:
    EngineExecutionError = RuntimeError  # type: ignore[misc,assignment]
    run_engine = None


TRACK_CONFIGS: Dict[str, Dict[str, Any]] = {
    "Real-Time Anomaly & Fraud Detection": {
        "mode_key": "anomaly_detection",
        "subtitle": (
            "High-throughput stream scoring pipeline for identifying statistical outliers, "
            "fraudulent transactions, and anomalous telemetry spikes."
        ),
        "default_threshold": 0.78,
        "default_intensity": 65,
        "primary_metric_label": "Detection Accuracy",
        "base_accuracy": 96.4,
    },
    "Quantitative Signal & Matrix Simulation": {
        "mode_key": "sort_stats",
        "subtitle": (
            "Low-latency Monte Carlo simulation, non-linear signal transformation, "
            "and high-speed numerical sorting benchmark."
        ),
        "default_threshold": 0.50,
        "default_intensity": 80,
        "primary_metric_label": "Convergence Score",
        "base_accuracy": 98.1,
    },
    "NLP Document & Log Triage": {
        "mode_key": "log_triage",
        "subtitle": (
            "Automated classification, token density scoring, and severity extraction "
            "across structured and unstructured text payloads."
        ),
        "default_threshold": 0.65,
        "default_intensity": 50,
        "primary_metric_label": "F1 Classification Score",
        "base_accuracy": 94.7,
    },
    "Supply Chain & Route Optimization": {
        "mode_key": "route_optim",
        "subtitle": (
            "Heuristic constraint solver for multi-node throughput balancing, "
            "latency reduction, and capacity allocation."
        ),
        "default_threshold": 0.70,
        "default_intensity": 75,
        "primary_metric_label": "Optimality Ratio",
        "base_accuracy": 95.8,
    },
}


def parse_uploaded_file(uploaded_file: Any) -> Dict[str, Any]:
    """Extract summary metadata and preview records from an uploaded CSV, JSON, or TXT file."""
    if uploaded_file is None:
        return {"filename": None, "row_count": 0, "preview": [], "raw_excerpt": None}

    filename: str = uploaded_file.name
    raw_bytes: bytes = uploaded_file.getvalue()
    text_content = raw_bytes.decode("utf-8", errors="replace")

    try:
        if filename.lower().endswith(".csv"):
            df = pd.read_csv(io.StringIO(text_content))
            return {
                "filename": filename,
                "row_count": int(len(df)),
                "columns": list(df.columns),
                "preview": df.head(20).to_dict(orient="records"),
                "dataframe": df.head(100),
            }
        if filename.lower().endswith(".json"):
            parsed = json.loads(text_content)
            records = parsed if isinstance(parsed, list) else [parsed]
            return {
                "filename": filename,
                "row_count": len(records),
                "preview": records[:10],
                "raw_excerpt": text_content[:1000],
            }
    except Exception as exc:
        return {
            "filename": filename,
            "row_count": 0,
            "error": f"Failed to parse structured file: {exc}",
            "raw_excerpt": text_content[:1000],
        }

    lines = [line for line in text_content.splitlines() if line.strip()]
    return {
        "filename": filename,
        "row_count": len(lines),
        "preview": lines[:15],
        "raw_excerpt": text_content[:1000],
    }


def mock_backend_process(
    track_name: str,
    threshold: float,
    intensity: int,
    sample_size: int,
    seed: int,
    file_meta: Dict[str, Any],
    use_native_engine: bool = False,
    timeout_seconds: float = 10.0,
) -> Dict[str, Any]:
    """Mock backend processor that works out-of-the-box and optionally calls core.bridge."""
    track_cfg = TRACK_CONFIGS[track_name]
    mode_key = track_cfg["mode_key"]
    start_ts = time.perf_counter()

    logs: List[str] = [
        f"[{datetime.now(timezone.utc).isoformat()}] Starting pipeline for track='{track_name}' (mode={mode_key})",
        f"[{datetime.now(timezone.utc).isoformat()}] Parameters: threshold={threshold:.2f}, intensity={intensity}, sample_size={sample_size}, seed={seed}",
    ]

    if file_meta.get("filename"):
        logs.append(
            f"[{datetime.now(timezone.utc).isoformat()}] Loaded input file '{file_meta['filename']}' ({file_meta.get('row_count', 0)} records)"
        )
    else:
        logs.append(
            f"[{datetime.now(timezone.utc).isoformat()}] No file uploaded; synthesizing benchmark dataset (n={sample_size})"
        )

    engine_payload: Optional[Dict[str, Any]] = None
    if use_native_engine and run_engine is not None:
        try:
            engine_payload = run_engine(
                ["--size", sample_size, "--seed", seed, "--mode", mode_key],
                timeout_seconds=timeout_seconds,
            )
            logs.append(
                f"[{datetime.now(timezone.utc).isoformat()}] C++ ./engine completed in "
                f"{engine_payload.get('metrics', {}).get('execution_time_ms', 0.0):.3f} ms"
            )
        except Exception as exc:
            logs.append(
                f"[{datetime.now(timezone.utc).isoformat()}] Native engine fallback triggered: {exc}"
            )

    # Simulate realistic compute latency proportional to intensity
    simulated_delay = 0.15 + (intensity / 100.0) * 0.25
    time.sleep(simulated_delay)

    rng = random.Random(seed)
    series_length = 40
    time_series: List[Dict[str, Any]] = []
    flagged_count = 0

    for step in range(series_length):
        wave = math.sin(step * 0.25 + (intensity * 0.05)) * 0.35 + 0.5
        noise = rng.uniform(-0.18, 0.18)
        score = max(0.0, min(1.0, round(wave + noise, 4)))
        baseline = round(0.45 + 0.15 * math.cos(step * 0.2), 4)
        is_flagged = score >= threshold
        if is_flagged:
            flagged_count += 1
        time_series.append(
            {
                "step": step + 1,
                "signal_score": score,
                "baseline": baseline,
                "threshold": threshold,
                "flagged": is_flagged,
            }
        )

    elapsed_ms = (time.perf_counter() - start_ts) * 1000.0
    if engine_payload and "metrics" in engine_payload:
        cpp_ms = float(engine_payload["metrics"].get("execution_time_ms", elapsed_ms))
        effective_ms = round(cpp_ms, 3)
    else:
        effective_ms = round(elapsed_ms, 2)

    # Compute deterministic accuracy / quality score from parameters
    base_acc = float(track_cfg["base_accuracy"])
    acc_modifier = (intensity - 50) * 0.025 - abs(threshold - track_cfg["default_threshold"]) * 3.5
    accuracy = max(80.0, min(99.9, round(base_acc + acc_modifier, 2)))

    throughput = int(round(sample_size / max(effective_ms / 1000.0, 0.001)))
    logs.append(
        f"[{datetime.now(timezone.utc).isoformat()}] Completed run: accuracy={accuracy:.2f}%, "
        f"flagged={flagged_count}/{series_length}, execution_time_ms={effective_ms}"
    )

    return {
        "status": "ok",
        "track": track_name,
        "mode": mode_key,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "parameters": {
            "threshold": threshold,
            "intensity": intensity,
            "sample_size": sample_size,
            "seed": seed,
            "use_native_engine": use_native_engine,
            "uploaded_file": file_meta.get("filename"),
        },
        "metrics": {
            "execution_time_ms": effective_ms,
            "accuracy_pct": accuracy,
            "flagged_events": flagged_count,
            "total_windows": series_length,
            "throughput_ops_sec": throughput,
        },
        "engine_output": engine_payload,
        "time_series": time_series,
        "logs": logs,
    }


def main() -> None:
    st.set_page_config(
        page_title="Hackathon Modular Prototype",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Initialize session state for settings and last run result
    if "api_endpoint" not in st.session_state:
        st.session_state["api_endpoint"] = "http://127.0.0.1:8000/api/v1/process"
    if "timeout_seconds" not in st.session_state:
        st.session_state["timeout_seconds"] = 10.0
    if "use_native_engine" not in st.session_state:
        st.session_state["use_native_engine"] = True

    # ---------------- Sidebar Controls ----------------
    with st.sidebar:
        st.header("Control Panel")

        selected_track = st.selectbox(
            "Problem Track / Mode",
            options=list(TRACK_CONFIGS.keys()),
            index=0,
            help="Switch the dashboard context and scoring heuristics across hackathon tracks.",
        )
        track_cfg = TRACK_CONFIGS[selected_track]

        st.subheader("Algorithm Parameters")
        threshold = st.slider(
            "Decision Threshold",
            min_value=0.05,
            max_value=0.95,
            value=float(track_cfg["default_threshold"]),
            step=0.05,
            help="Sensitivity cutoff for flagging events or signals.",
        )
        intensity = st.slider(
            "Compute / Mode Intensity",
            min_value=10,
            max_value=100,
            value=int(track_cfg["default_intensity"]),
            step=5,
            help="Controls simulation depth and iterative refinement passes.",
        )
        sample_size = st.select_slider(
            "Synthetic Batch Size (N)",
            options=[10_000, 50_000, 100_000, 250_000, 500_000, 1_000_000],
            value=100_000,
        )
        seed = int(
            st.number_input(
                "Random Seed",
                min_value=1,
                max_value=999_999,
                value=42,
                step=1,
            )
        )

        st.subheader("Dataset Ingestion")
        uploaded_file = st.file_uploader(
            "Upload Input Payload (CSV, JSON, TXT)",
            type=["csv", "json", "txt"],
            help="Optional custom dataset to override or augment synthetic generation.",
        )

        run_clicked = st.button("Run Pipeline", type="primary", use_container_width=True)

    # ---------------- Main Area: Dynamic Header ----------------
    st.title(f"⚡ {selected_track}")
    st.caption(track_cfg["subtitle"])

    file_meta = parse_uploaded_file(uploaded_file)

    # Execute pipeline automatically on first load, track change, or explicit button click
    state_key = f"{selected_track}:{threshold}:{intensity}:{sample_size}:{seed}:{file_meta.get('filename')}"
    if run_clicked or st.session_state.get("last_state_key") != state_key:
        with st.spinner(f"Executing {track_cfg['mode_key']} pipeline..."):
            result = mock_backend_process(
                track_name=selected_track,
                threshold=threshold,
                intensity=intensity,
                sample_size=sample_size,
                seed=seed,
                file_meta=file_meta,
                use_native_engine=bool(st.session_state["use_native_engine"]),
                timeout_seconds=float(st.session_state["timeout_seconds"]),
            )
            st.session_state["last_result"] = result
            st.session_state["last_state_key"] = state_key

    result = st.session_state["last_result"]
    metrics = result["metrics"]

    # ---------------- Main Area: Status & Metric Cards ----------------
    status_col, badge_col = st.columns([3, 1])
    with status_col:
        st.success(
            f"Pipeline Status: **ONLINE** — Mode `{result['mode']}` completed at `{result['timestamp_utc']}`"
        )
    with badge_col:
        engine_mode_label = (
            "Native C++ `./engine`" if result.get("engine_output") else "Python Mock Engine"
        )
        st.info(f"Runtime: **{engine_mode_label}**")

    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    m_col1.metric(
        label="Execution Time",
        value=f"{metrics['execution_time_ms']:.2f} ms",
        delta=f"{round(15.0 - metrics['execution_time_ms'], 2)} ms vs baseline",
        delta_color="normal",
    )
    m_col2.metric(
        label=track_cfg["primary_metric_label"],
        value=f"{metrics['accuracy_pct']:.2f}%",
        delta=f"{round(metrics['accuracy_pct'] - track_cfg['base_accuracy'], 2)}%",
    )
    m_col3.metric(
        label="Flagged Events",
        value=f"{metrics['flagged_events']} / {metrics['total_windows']}",
        delta=f"Threshold ≥ {threshold:.2f}",
        delta_color="off",
    )
    m_col4.metric(
        label="Effective Throughput",
        value=f"{metrics['throughput_ops_sec']:,} ops/s",
        delta=f"N = {sample_size:,}",
        delta_color="off",
    )

    # ---------------- Main Area: 3-Tab Layout ----------------
    tab_viz, tab_raw, tab_settings = st.tabs(
        [
            "📈 Live Output / Visualizations",
            "🧾 Raw Log / JSON Output",
            "⚙️ Settings / API Config",
        ]
    )

    with tab_viz:
        st.subheader("Signal Score vs. Decision Threshold")
        ts_df = pd.DataFrame(result["time_series"]).set_index("step")
        st.line_chart(ts_df[["signal_score", "baseline", "threshold"]], height=320)

        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown("#### Flagged Window Breakdown")
            flagged_df = ts_df[ts_df["flagged"]].reset_index()
            if not flagged_df.empty:
                st.dataframe(flagged_df, use_container_width=True, hide_index=True)
            else:
                st.info("No windows exceeded the current decision threshold.")

        with col_right:
            st.markdown("#### Uploaded File / Batch Preview")
            if file_meta.get("filename"):
                st.write(
                    f"**File:** `{file_meta['filename']}` — **Records:** `{file_meta.get('row_count', 0)}`"
                )
                if "dataframe" in file_meta:
                    st.dataframe(file_meta["dataframe"], use_container_width=True, height=240)
                elif file_meta.get("preview"):
                    st.json(file_meta["preview"])
            elif result.get("engine_output"):
                st.write("**C++ Engine Summary Metrics & Top-5 Sample:**")
                st.json(result["engine_output"])
            else:
                st.caption(
                    "Upload a CSV, JSON, or TXT file in the sidebar to inspect custom payload records here."
                )

    with tab_raw:
        st.subheader("Execution Trace Logs")
        st.code("\n".join(result["logs"]), language="log")

        st.subheader("Full JSON Response Payload")
        json_str = json.dumps(result, indent=2)
        st.download_button(
            label="Download JSON Output",
            data=json_str,
            file_name=f"{result['mode']}_output.json",
            mime="application/json",
        )
        st.json(result)

    with tab_settings:
        st.subheader("Runtime & FastAPI Backend Configuration")
        st.markdown(
            "Configure how the Streamlit frontend communicates with `main.py` (FastAPI) "
            "and `core/bridge.py` (C++ `./engine` subprocess wrapper)."
        )

        api_url = st.text_input(
            "FastAPI Endpoint URL",
            value=st.session_state["api_endpoint"],
            help="Target endpoint used when switching from local mock/bridge mode to HTTP API mode.",
        )
        timeout_val = st.number_input(
            "Subprocess / Request Timeout (seconds)",
            min_value=1.0,
            max_value=120.0,
            value=float(st.session_state["timeout_seconds"]),
            step=1.0,
        )
        native_toggle = st.toggle(
            "Prefer compiled C++ `./engine` binary via `core/bridge.py` when present",
            value=bool(st.session_state["use_native_engine"]),
        )

        if st.button("Save Configuration"):
            st.session_state["api_endpoint"] = api_url
            st.session_state["timeout_seconds"] = float(timeout_val)
            st.session_state["use_native_engine"] = bool(native_toggle)
            st.success("Runtime settings updated.")

        st.markdown("#### Environment Diagnostics")
        st.json(
            {
                "fastapi_endpoint": st.session_state["api_endpoint"],
                "timeout_seconds": st.session_state["timeout_seconds"],
                "use_native_engine": st.session_state["use_native_engine"],
                "core_bridge_importable": run_engine is not None,
                "active_track_mode": result["mode"],
            }
        )


if __name__ == "__main__":
    main()