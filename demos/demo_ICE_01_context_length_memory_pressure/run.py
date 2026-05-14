from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import resource
import socket
import statistics
import sys
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
CONFIG_DIR = ROOT / "configs"
WITNESS_DIR = ROOT / "witnesses"
RESULTS_DIR = ROOT / "results"

CLAIM_ID = "K_context_length_memory_pressure"
JUDGMENT_FORM = (
    "Γ_ICE-P1 ⊢ K_context_length_memory_pressure @ B_demo_ICE_01 "
    "⇐ W_demo_ICE_01 : σ"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sha256_json(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256_bytes(encoded)


def anonymized_hostname() -> str:
    return "host-" + sha256_bytes(socket.gethostname().encode("utf-8"))[:12]


def maxrss_bytes() -> int | None:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if value <= 0:
        return None
    if sys.platform == "darwin":
        return int(value)
    return int(value) * 1024


def median(values: list[float]) -> float:
    return float(statistics.median(values)) if values else 0.0


def relative_spread(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = statistics.fmean(values)
    if math.isclose(mean, 0.0, abs_tol=1e-12):
        return 0.0
    return float(statistics.pstdev(values) / abs(mean))


def touch_memory(buffer: bytearray) -> None:
    step = 4096
    for offset in range(0, len(buffer), step):
        buffer[offset] = (offset // step) % 251
    if buffer:
        buffer[-1] = 1


def synthetic_attention_like_workload(length: int, batch_size: int, bytes_per_score: int, abort_limit_bytes: int) -> dict[str, Any]:
    allocation_bytes = batch_size * length * length * bytes_per_score
    if allocation_bytes > abort_limit_bytes:
        return {
            "length": length,
            "allocation_bytes": allocation_bytes,
            "aborted": True,
            "abort_reason": "abort_limit_exceeded",
            "latency_ms": None,
            "peak_memory_delta_bytes": None,
            "peak_rss_delta_bytes": None,
        }

    tracemalloc.start()
    start_current, start_peak = tracemalloc.get_traced_memory()
    rss_before = maxrss_bytes()
    started = time.perf_counter()
    buffer = bytearray(allocation_bytes)
    touch_memory(buffer)
    latency_ms = (time.perf_counter() - started) * 1000.0
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    rss_after = maxrss_bytes()
    del buffer

    peak_delta = max(0, peak - start_current)
    rss_delta = None
    if rss_before is not None and rss_after is not None:
        rss_delta = max(0, rss_after - rss_before)

    return {
        "length": length,
        "allocation_bytes": allocation_bytes,
        "aborted": False,
        "abort_reason": None,
        "latency_ms": round(latency_ms, 6),
        "peak_memory_delta_bytes": int(peak_delta),
        "peak_rss_delta_bytes": rss_delta,
    }


def witness_record(witness_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    record = {
        "witness_id": witness_id,
        "created_at_utc": utc_now(),
        "payload": payload,
    }
    record["content_hash"] = sha256_json(record)
    return record


def evaluate_condition(peak_bytes: float, control_median: float, contract: dict[str, Any]) -> bool:
    m_abs = float(contract["M_abs_bytes"])
    ratio = float(contract["R_ratio"])
    if control_median <= 0:
        return peak_bytes >= m_abs
    return peak_bytes >= m_abs and peak_bytes >= ratio * control_median


def main() -> None:
    boundary_path = CONFIG_DIR / "boundary.json"
    contract_path = CONFIG_DIR / "contract.json"
    boundary = load_json(boundary_path)
    contract = load_json(contract_path)

    WITNESS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    trace_lines: list[str] = []
    trace_lines.append("demo_ICE_01 start")

    control_lengths = [int(x) for x in boundary["input_lengths_control"]]
    test_lengths = [int(x) for x in boundary["input_lengths_test"]]
    repetitions = int(boundary["repetitions"])
    warmup_runs = int(boundary["warmup_runs"])
    batch_size = int(boundary["batch_size"])
    embedding_dim = int(boundary["embedding_dim"])
    bytes_per_score = int(boundary["bytes_per_score"])
    abort_limit_bytes = int(boundary["abort_limit_bytes"])

    run_order = []
    all_lengths = [("control", length) for length in control_lengths] + [("test", length) for length in test_lengths]
    measurements: list[dict[str, Any]] = []

    for group, length in all_lengths:
        trace_lines.append(f"warmup group={group} length={length}")
        for _ in range(warmup_runs):
            synthetic_attention_like_workload(length, batch_size, bytes_per_score, abort_limit_bytes)

        for rep in range(1, repetitions + 1):
            trace_lines.append(f"measure group={group} length={length} repetition={rep}")
            result = synthetic_attention_like_workload(length, batch_size, bytes_per_score, abort_limit_bytes)
            result["group"] = group
            result["repetition"] = rep
            measurements.append(result)
            run_order.append({"group": group, "length": length, "repetition": rep})

    control_successes = [m for m in measurements if m["group"] == "control" and not m["aborted"]]
    test_successes = [m for m in measurements if m["group"] == "test" and not m["aborted"]]
    control_peaks = [float(m["peak_memory_delta_bytes"]) for m in control_successes if m["peak_memory_delta_bytes"] is not None]
    control_median = median(control_peaks)
    control_spread = relative_spread(control_peaks)

    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in measurements:
        grouped.setdefault((row["group"], int(row["length"])), []).append(row)

    length_evaluations = []
    for (group, length), rows in sorted(grouped.items(), key=lambda item: (item[0][0], item[0][1])):
        successful = [row for row in rows if not row["aborted"] and row["peak_memory_delta_bytes"] is not None]
        peaks = [float(row["peak_memory_delta_bytes"]) for row in successful]
        median_peak = median(peaks)
        holds_c = False
        if successful:
            holds_c = evaluate_condition(median_peak, control_median, contract)
        length_evaluations.append({
            "group": group,
            "length": length,
            "successful_repetitions": len(successful),
            "aborted_repetitions": sum(1 for row in rows if row["aborted"]),
            "median_peak_memory_delta_bytes": median_peak if successful else None,
            "relative_spread": relative_spread(peaks),
            "holds_condition_c": holds_c if successful else None,
        })

    control_evals = [row for row in length_evaluations if row["group"] == "control"]
    test_evals = [row for row in length_evaluations if row["group"] == "test"]
    controls_satisfy_c = any(bool(row["holds_condition_c"]) for row in control_evals if row["holds_condition_c"] is not None)
    tests_satisfy_c = [row for row in test_evals if bool(row["holds_condition_c"])]
    too_noisy = any(float(row["relative_spread"]) > 0.15 for row in length_evaluations if row["median_peak_memory_delta_bytes"] is not None)
    all_test_aborted = bool(test_evals) and all(row["successful_repetitions"] == 0 for row in test_evals)

    status = "checked"
    if all_test_aborted:
        status = "out_of_scope"
    elif controls_satisfy_c or too_noisy:
        status = "inconclusive"
    elif not tests_satisfy_c:
        status = "failed"

    required_witness_names = [
        "input_profile.json",
        "execution_trace.json",
        "map.json",
        "contract.json",
        "check.json",
        "ruleout.json",
    ]

    input_payload = {
        "input_lengths_control": control_lengths,
        "input_lengths_test": test_lengths,
        "batch_size": batch_size,
        "embedding_dim": embedding_dim,
        "bytes_per_score": bytes_per_score,
        "synthetic_input_policy": "Deterministic length-only synthetic profiles with fixed run order and no external data.",
        "repetitions": repetitions,
        "run_order": run_order,
    }
    exec_payload = {
        "runtime_metadata": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "execution_device": boundary["execution_device"],
            "runtime": boundary["runtime"],
        },
        "measurements": measurements,
        "control_median_peak_memory_delta_bytes": control_median,
        "control_relative_spread": control_spread,
        "abort_limit_bytes": abort_limit_bytes,
    }
    map_payload = {
        "context_length_symbol": "l",
        "shape_logic": "allocation_bytes = batch_size * l * l * bytes_per_score",
        "growth_model": "O(l^2)",
        "condition_id": contract["condition_id"],
        "condition_mapping": "Longer input length increases synthetic score-allocation size and can induce memory-pressure regime C.",
    }
    contract_payload = {
        **contract,
        "measurement_method": boundary["measurement_method"],
        "validity_constraints": [
            "thresholds are predeclared",
            "same runtime and workload function across control and test",
            "same device class across control and test",
        ],
        "failure_conditions": [
            "no test length satisfies condition C",
            "all test lengths abort before meaningful measurement",
            "controls satisfy condition C",
        ],
    }
    check_payload = {
        "control_lengths_evaluation": control_evals,
        "test_lengths_evaluation": test_evals,
        "controls_satisfy_c": controls_satisfy_c,
        "tests_satisfying_c": tests_satisfy_c,
        "repetition_consistency": {
            "control_relative_spread": control_spread,
            "too_noisy": too_noisy,
        },
    }
    ruleout_payload = {
        "same_runtime": True,
        "same_workload_function": True,
        "same_dtype_simulation": True,
        "same_measurement_method": True,
        "same_device_class": True,
        "no_network": True,
        "no_external_workload": True,
        "thresholds_predeclared": bool(contract["thresholds_predeclared"]),
        "boundary_unchanged": True,
    }

    witnesses = {
        "input_profile.json": witness_record("W_input", input_payload),
        "execution_trace.json": witness_record("W_exec", exec_payload),
        "map.json": witness_record("W_map", map_payload),
        "contract.json": witness_record("W_contract", contract_payload),
        "check.json": witness_record("W_check", check_payload),
        "ruleout.json": witness_record("W_ruleout", ruleout_payload),
    }

    for filename, payload in witnesses.items():
        write_json(WITNESS_DIR / filename, payload)

    missing_witnesses = [name for name in required_witness_names if not (WITNESS_DIR / name).exists()]
    if missing_witnesses:
        status = "incomplete"

    boundary_hash = sha256_file(boundary_path)
    contract_hash = sha256_file(contract_path)
    environment_payload = {
        "timestamp_utc": utc_now(),
        "platform": platform.platform(),
        "python_version": sys.version,
        "runtime": boundary["runtime"],
        "boundary_sha256": boundary_hash,
        "contract_sha256": contract_hash,
        "hostname_redacted_or_anonymized": anonymized_hostname(),
        "cwd": str(ROOT),
        "notes": {
            "no_training": True,
            "no_external_data": True,
            "no_network_required": True,
        },
    }
    write_json(RESULTS_DIR / "environment.json", environment_payload)

    summary = {
        "claim_id": CLAIM_ID,
        "status": status,
        "control_lengths": control_lengths,
        "test_lengths": test_lengths,
        "tests_satisfying_c": [row["length"] for row in tests_satisfy_c],
        "controls_satisfy_c": controls_satisfy_c,
        "control_median_peak_memory_delta_bytes": control_median,
        "all_test_aborted": all_test_aborted,
        "too_noisy": too_noisy,
    }
    write_json(RESULTS_DIR / "summary.json", summary)

    trace_lines.append(f"status={status}")
    trace_lines.append(f"control_median_peak_memory_delta_bytes={control_median}")
    trace_lines.append(f"tests_satisfying_c={[row['length'] for row in tests_satisfy_c]}")
    (RESULTS_DIR / "trace.log").write_text("\n".join(trace_lines) + "\n", encoding="utf-8")

    judgment = {
        "upl_namespace": "UPL-ICE",
        "profile": "ICE-P1",
        "claim_id": CLAIM_ID,
        "claim": "Increasing input context length beyond threshold L induces memory-pressure regime C under boundary B.",
        "boundary_id": boundary["boundary_id"],
        "judgment_form": JUDGMENT_FORM,
        "witnesses": {
            "input": "witnesses/input_profile.json",
            "exec": "witnesses/execution_trace.json",
            "map": "witnesses/map.json",
            "contract": "witnesses/contract.json",
            "check": "witnesses/check.json",
            "ruleout": "witnesses/ruleout.json"
        },
        "status": status,
        "allowed_claims": [
            "input length induced memory-pressure condition C within B"
        ],
        "forbidden_claims": [
            "input caused unsafe AI output",
            "chip is unsafe",
            "model is unsafe",
            "cyberattack occurred",
            "result generalizes beyond B"
        ],
        "notes": {
            "no_training": True,
            "no_external_data": True,
            "no_push": True,
        }
    }
    write_json(RESULTS_DIR / "judgment.json", judgment)

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
