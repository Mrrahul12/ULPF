"""
ULPF STEP 17 - HPA STRESS TEST

Generates real concurrent /parse traffic from inside the Kubernetes cluster
and monitors CPU usage + HPA replica decisions.

Prerequisites:
    - Docker Desktop Kubernetes running
    - namespace: ulpf
    - deployment/service: ulpf
    - HPA: ulpf
    - kubectl available
    - metrics-server available

The test:
    1. Captures the baseline.
    2. Creates an in-cluster Python load generator.
    3. Sends concurrent requests to http://ulpf:8000/parse.
    4. Monitors HPA and pod CPU.
    5. Waits for scale-up.
    6. Stops traffic.
    7. Waits for scale-down.
    8. Writes a machine-readable JSON report.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


NAMESPACE = "ulpf"
DEPLOYMENT = "ulpf"
SERVICE = "ulpf"
HPA = "ulpf"

RESULT_DIR = Path(__file__).parent / "step17-results"


LOAD_SCRIPT = r'''
import concurrent.futures
import json
import threading
import time
import urllib.request
import urllib.error

URL = "http://ulpf:8000/parse"
DURATION = DURATION_PLACEHOLDER
WORKERS = WORKERS_PLACEHOLDER

PAYLOAD = json.dumps({
    "message": "2026-09-10T18:00:00Z firewall01 INFO source=10.10.10.25 destination=192.168.1.10 action=ALLOW protocol=TCP port=443 bytes=2048 event=hpa-stress-test"
}).encode()

total = 0
success = 0
failure = 0

latencies = []
status_counts = {}
error_counts = {}

lock = threading.Lock()

stop_at = time.time() + DURATION


def request_once():
    global total, success, failure

    if time.time() >= stop_at:
        return

    started = time.perf_counter()

    try:
        req = urllib.request.Request(
            URL,
            data=PAYLOAD,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.status
            response.read()

        latency = (time.perf_counter() - started) * 1000

        with lock:
            total += 1

            status_counts[str(status)] = (
                status_counts.get(str(status), 0) + 1
            )

            if 200 <= status < 300:
                success += 1
                latencies.append(latency)
            else:
                failure += 1

    except urllib.error.HTTPError as exc:
        with lock:
            total += 1
            failure += 1

            status_counts[str(exc.code)] = (
                status_counts.get(str(exc.code), 0) + 1
            )

            try:
                body = exc.read().decode(
                    "utf-8",
                    errors="replace",
                )[:300]
            except Exception:
                body = ""

            key = f"HTTP {exc.code}: {body}"
            error_counts[key] = error_counts.get(key, 0) + 1

    except urllib.error.URLError as exc:
        with lock:
            total += 1
            failure += 1

            key = f"URLError: {exc.reason}"
            error_counts[key] = error_counts.get(key, 0) + 1

    except Exception as exc:
        with lock:
            total += 1
            failure += 1

            key = f"{type(exc).__name__}: {str(exc)}"
            error_counts[key] = error_counts.get(key, 0) + 1


started_at = time.time()

with concurrent.futures.ThreadPoolExecutor(
    max_workers=WORKERS
) as executor:

    futures = []

    while time.time() < stop_at:

        for _ in range(WORKERS * 4):

            if time.time() >= stop_at:
                break

            futures.append(
                executor.submit(request_once)
            )

        if len(futures) > WORKERS * 20:

            done, pending = concurrent.futures.wait(
                futures,
                timeout=0.1,
            )

            futures = list(pending)

    concurrent.futures.wait(futures)


elapsed = max(
    time.time() - started_at,
    0.001,
)

latencies_sorted = sorted(latencies)

if latencies_sorted:

    p95_index = min(
        len(latencies_sorted) - 1,
        int(len(latencies_sorted) * 0.95),
    )

    p95 = latencies_sorted[p95_index]

    average = (
        sum(latencies_sorted)
        / len(latencies_sorted)
    )

    maximum = max(latencies_sorted)

else:

    average = 0
    p95 = 0
    maximum = 0


result = {
    "duration_seconds": elapsed,
    "workers": WORKERS,
    "total_requests": total,
    "successful_requests": success,
    "failed_requests": failure,
    "status_counts": status_counts,
    "error_counts": error_counts,
    "requests_per_second": total / elapsed,
    "average_latency_ms": average,
    "p95_latency_ms": p95,
    "max_latency_ms": maximum,
}

print(json.dumps(result))
'''


def run_kubectl(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["kubectl", *args],
        capture_output=True,
        text=True,
        check=False,
    )

    if check and result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise RuntimeError(
            f"kubectl command failed: kubectl {' '.join(args)}"
        )

    return result.stdout.strip()


def get_hpa() -> dict:
    raw = run_kubectl(
        "get",
        "hpa",
        HPA,
        "-n",
        NAMESPACE,
        "-o",
        "json",
    )

    obj = json.loads(raw)

    status = obj.get("status", {})

    return {
        "current_replicas": status.get("currentReplicas", 0),
        "desired_replicas": status.get("desiredReplicas", 0),
        "min_replicas": obj.get("spec", {}).get("minReplicas"),
        "max_replicas": obj.get("spec", {}).get("maxReplicas"),
        "current_cpu": None,
        "target_cpu": None,
    }


def get_cpu_usage() -> dict:
    try:
        output = run_kubectl(
            "top",
            "pods",
            "-n",
            NAMESPACE,
            "-l",
            f"app={DEPLOYMENT}",
            "--no-headers",
            check=False,
        )

        pods = []

        for line in output.splitlines():
            parts = line.split()

            if len(parts) >= 3:
                pods.append(
                    {
                        "pod": parts[0],
                        "cpu": parts[1],
                        "memory": parts[2],
                    }
                )

        return {
            "pods": pods,
            "raw": output,
        }

    except Exception as exc:
        return {
            "pods": [],
            "error": str(exc),
        }


def get_deployment_replicas() -> dict:
    raw = run_kubectl(
        "get",
        "deployment",
        DEPLOYMENT,
        "-n",
        NAMESPACE,
        "-o",
        "json",
    )

    obj = json.loads(raw)
    status = obj.get("status", {})

    return {
        "desired": obj.get("spec", {}).get("replicas", 0),
        "current": status.get("replicas", 0),
        "ready": status.get("readyReplicas", 0),
        "available": status.get("availableReplicas", 0),
    }


def snapshot() -> dict:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hpa": get_hpa(),
        "deployment": get_deployment_replicas(),
        "cpu": get_cpu_usage(),
    }


def wait_for_scale_up(
    baseline: int,
    timeout: int,
    interval: int,
    snapshots: list,
) -> tuple[bool, float | None]:

    started = time.time()

    while time.time() - started < timeout:
        snap = snapshot()
        snapshots.append(snap)

        current = snap["hpa"]["current_replicas"]
        desired = snap["hpa"]["desired_replicas"]

        elapsed = round(time.time() - started, 1)

        print(
            f"[SCALE-UP] +{elapsed}s | "
            f"current={current} desired={desired}"
        )

        if current > baseline or desired > baseline:
            return True, time.time() - started

        time.sleep(interval)

    return False, None


def wait_for_scale_down(
    baseline: int,
    timeout: int,
    interval: int,
    snapshots: list,
) -> tuple[bool, float | None]:

    started = time.time()

    while time.time() - started < timeout:
        snap = snapshot()
        snapshots.append(snap)

        current = snap["hpa"]["current_replicas"]
        desired = snap["hpa"]["desired_replicas"]

        elapsed = round(time.time() - started, 1)

        print(
            f"[SCALE-DOWN] +{elapsed}s | "
            f"current={current} desired={desired}"
        )

        if current <= baseline and desired <= baseline:
            return True, time.time() - started

        time.sleep(interval)

    return False, None


def create_load_job(duration: int, workers: int) -> str:
    script = LOAD_SCRIPT.replace(
        "DURATION_PLACEHOLDER",
        str(duration),
    ).replace(
        "WORKERS_PLACEHOLDER",
        str(workers),
    )

    encoded = script.replace("\\", "\\\\").replace("'", "'\\''")

    pod_name = "ulpf-hpa-load"

    run_kubectl(
        "delete",
        "pod",
        pod_name,
        "-n",
        NAMESPACE,
        "--ignore-not-found=true",
        check=False,
    )

    command = (
        "python -c "
        f"'{encoded}'"
    )

    print(
        f"\nStarting in-cluster load generator: "
        f"{workers} workers for {duration}s"
    )

    run_kubectl(
        "run",
        pod_name,
        "-n",
        NAMESPACE,
        "--image=python:3.12-alpine",
        "--restart=Never",
        "--command",
        "--",
        "sh",
        "-c",
        command,
    )

    return pod_name


def wait_for_load_completion(pod_name: str, timeout: int) -> dict:
    started = time.time()

    while time.time() - started < timeout:
        result = subprocess.run(
            [
                "kubectl",
                "get",
                "pod",
                pod_name,
                "-n",
                NAMESPACE,
                "-o",
                "json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            obj = json.loads(result.stdout)
            phase = obj.get("status", {}).get("phase")

            if phase in {"Succeeded", "Failed"}:
                logs = run_kubectl(
                    "logs",
                    pod_name,
                    "-n",
                    NAMESPACE,
                    check=False,
                )

                try:
                    return json.loads(logs.splitlines()[-1])
                except Exception:
                    return {
                        "raw_logs": logs,
                        "phase": phase,
                    }

        time.sleep(2)

    return {
        "timeout": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ULPF Step 17 HPA stress test"
    )

    parser.add_argument(
        "--duration",
        type=int,
        default=180,
        help="Load duration in seconds",
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=50,
        help="Concurrent worker count",
    )

    parser.add_argument(
        "--scale-up-timeout",
        type=int,
        default=180,
        help="Maximum seconds to wait for scale-up",
    )

    parser.add_argument(
        "--scale-down-timeout",
        type=int,
        default=360,
        help="Maximum seconds to wait for scale-down",
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="HPA monitoring interval",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("ULPF STEP 17 - HPA STRESS TEST")
    print("=" * 70)

    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------
    # Baseline
    # ---------------------------------------------------------------

    print("\n[1] Capturing baseline...")

    baseline_snapshot = snapshot()

    baseline_replicas = baseline_snapshot["deployment"]["ready"]

    print(
        f"Baseline ready replicas: {baseline_replicas}"
    )

    print(
        f"HPA current/desired: "
        f"{baseline_snapshot['hpa']['current_replicas']}/"
        f"{baseline_snapshot['hpa']['desired_replicas']}"
    )

    # ---------------------------------------------------------------
    # Load
    # ---------------------------------------------------------------

    print("\n[2] Starting concurrent in-cluster load...")

    pod_name = create_load_job(
        args.duration,
        args.workers,
    )

    snapshots = [baseline_snapshot]

    print("\n[3] Waiting for HPA scale-up...")

    scale_up, scale_up_seconds = wait_for_scale_up(
        baseline_replicas,
        args.scale_up_timeout,
        args.interval,
        snapshots,
    )

    print("\n[4] Waiting for load generator to finish...")

    load_result = wait_for_load_completion(
        pod_name,
        args.duration + 120,
    )

    print(
        "\nLoad result:",
        json.dumps(load_result, indent=2),
    )

    # ---------------------------------------------------------------
    # Scale down
    # ---------------------------------------------------------------

    print("\n[5] Waiting for HPA scale-down...")

    scale_down, scale_down_seconds = wait_for_scale_down(
        baseline_replicas,
        args.scale_down_timeout,
        args.interval,
        snapshots,
    )

    final_snapshot = snapshot()

    # ---------------------------------------------------------------
    # Cleanup
    # ---------------------------------------------------------------

    run_kubectl(
        "delete",
        "pod",
        pod_name,
        "-n",
        NAMESPACE,
        "--ignore-not-found=true",
        check=False,
    )

    # ---------------------------------------------------------------
    # Acceptance criteria
    # ---------------------------------------------------------------

    load_success = (
        load_result.get("failed_requests", 1) == 0
    )

    rollout_healthy = (
        final_snapshot["deployment"]["ready"] >= baseline_replicas
    )

    scale_up_pass = scale_up

    scale_down_pass = scale_down

    overall_pass = (
        scale_up_pass
        and scale_down_pass
        and load_success
        and rollout_healthy
    )

    report = {
        "step": 17,
        "test": "HPA Stress Testing",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "configuration": {
            "namespace": NAMESPACE,
            "deployment": DEPLOYMENT,
            "service": SERVICE,
            "hpa": HPA,
            "duration_seconds": args.duration,
            "workers": args.workers,
            "scale_up_timeout": args.scale_up_timeout,
            "scale_down_timeout": args.scale_down_timeout,
            "monitor_interval": args.interval,
        },
        "baseline": baseline_snapshot,
        "load_result": load_result,
        "scale_up": {
            "passed": scale_up_pass,
            "seconds": scale_up_seconds,
        },
        "scale_down": {
            "passed": scale_down_pass,
            "seconds": scale_down_seconds,
        },
        "final": final_snapshot,
        "acceptance": {
            "hpa_scaled_up": scale_up_pass,
            "hpa_scaled_down": scale_down_pass,
            "load_had_no_failures": load_success,
            "deployment_healthy": rollout_healthy,
        },
        "overall_pass": overall_pass,
        "snapshots": snapshots,
    }

    filename = (
        "step17-hpa-result-"
        + datetime.now().strftime("%Y%m%d-%H%M%S")
        + ".json"
    )

    output = RESULT_DIR / filename

    output.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("\n" + "=" * 70)
    print("STEP 17 RESULT")
    print("=" * 70)

    print(
        f"HPA scale-up : {'PASS' if scale_up_pass else 'FAIL'}"
    )

    print(
        f"HPA scale-down: {'PASS' if scale_down_pass else 'FAIL'}"
    )

    print(
        f"Load success  : {'PASS' if load_success else 'FAIL'}"
    )

    print(
        f"Deployment    : {'PASS' if rollout_healthy else 'FAIL'}"
    )

    print(
        f"\nOverall       : "
        f"{'PASS' if overall_pass else 'REVIEW'}"
    )

    print(f"\nReport saved: {output}")

    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())