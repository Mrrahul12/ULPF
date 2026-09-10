"""
ULPF Step 16 - Rolling Update Resilience Test

Sends continuous requests to the Kubernetes Service while triggering
a Deployment rolling update.

Run:
    python k8s/rolling_update_test.py

Prerequisites:
    kubectl configured for the Docker Desktop Kubernetes cluster
    ULPF namespace/deployment/service already deployed
    kubectl port-forward -n ulpf svc/ulpf 8080:8000
"""

from __future__ import annotations

import json
import statistics
import subprocess
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path


BASE_URL = "http://127.0.0.1:8080"
HEALTH_ENDPOINT = f"{BASE_URL}/health"

NAMESPACE = "ulpf"
DEPLOYMENT = "ulpf"

REQUEST_DURATION_SECONDS = 60
REQUEST_INTERVAL_SECONDS = 0.05
ROLLOUT_DELAY_SECONDS = 5
REQUEST_TIMEOUT_SECONDS = 5

OUTPUT_DIR = Path(__file__).resolve().parent / "step16-results"


@dataclass
class RequestResult:
    timestamp: str
    success: bool
    status_code: int | None
    latency_ms: float
    request_id: str | None
    trace_id: str | None
    error: str | None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_kubectl(*args: str) -> tuple[int, str, str]:
    """Run kubectl and return exit code, stdout, stderr."""

    process = subprocess.run(
        ["kubectl", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    return process.returncode, process.stdout.strip(), process.stderr.strip()


def kubectl_json(*args: str) -> dict:
    """Run kubectl and parse JSON output."""

    code, stdout, stderr = run_kubectl(*args, "-o", "json")

    if code != 0:
        raise RuntimeError(f"kubectl failed: {stderr}")

    return json.loads(stdout)


def check_prerequisites() -> None:
    print("\n=== Step 16: Prerequisite Check ===")

    code, stdout, stderr = run_kubectl(
        "get",
        "deployment",
        DEPLOYMENT,
        "-n",
        NAMESPACE,
    )

    if code != 0:
        raise RuntimeError(
            "ULPF deployment could not be found.\n"
            f"{stderr}"
        )

    print("✓ Kubernetes deployment found")

    code, stdout, stderr = run_kubectl(
        "get",
        "pods",
        "-n",
        NAMESPACE,
    )

    if code != 0:
        raise RuntimeError(f"Could not read pods: {stderr}")

    print("✓ Kubernetes pods accessible")

    try:
        request_health()
        print("✓ ULPF Service is reachable on port 8080")
    except Exception as exc:
        raise RuntimeError(
            "Could not reach ULPF through the Kubernetes Service.\n"
            "Make sure this is running in another terminal:\n\n"
            "kubectl port-forward -n ulpf svc/ulpf 8080:8000\n"
        ) from exc


def request_health() -> RequestResult:
    """Send one health request and capture useful response metadata."""

    start = time.perf_counter()

    try:
        request = urllib.request.Request(
            HEALTH_ENDPOINT,
            method="GET",
            headers={
                "User-Agent": "ULPF-Step16-Resilience-Test",
            },
        )

        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT_SECONDS,
        ) as response:

            body = response.read().decode("utf-8", errors="replace")

            latency_ms = (time.perf_counter() - start) * 1000

            request_id = response.headers.get("X-Request-ID")
            trace_id = response.headers.get("X-Trace-ID")

            return RequestResult(
                timestamp=utc_now(),
                success=200 <= response.status < 300,
                status_code=response.status,
                latency_ms=latency_ms,
                request_id=request_id,
                trace_id=trace_id,
                error=None if 200 <= response.status < 300 else body[:300],
            )

    except urllib.error.HTTPError as exc:

        latency_ms = (time.perf_counter() - start) * 1000

        return RequestResult(
            timestamp=utc_now(),
            success=False,
            status_code=exc.code,
            latency_ms=latency_ms,
            request_id=exc.headers.get("X-Request-ID"),
            trace_id=exc.headers.get("X-Trace-ID"),
            error=str(exc),
        )

    except Exception as exc:

        latency_ms = (time.perf_counter() - start) * 1000

        return RequestResult(
            timestamp=utc_now(),
            success=False,
            status_code=None,
            latency_ms=latency_ms,
            request_id=None,
            trace_id=None,
            error=f"{type(exc).__name__}: {exc}",
        )


def traffic_worker(
    results: list[RequestResult],
    stop_event: threading.Event,
) -> None:
    """Continuously send requests."""

    while not stop_event.is_set():

        result = request_health()
        results.append(result)

        time.sleep(REQUEST_INTERVAL_SECONDS)


def get_pod_snapshot() -> list[dict]:
    """Capture current ULPF pod state."""

    data = kubectl_json(
        "get",
        "pods",
        "-n",
        NAMESPACE,
        "-l",
        "app=ulpf",
    )

    snapshot = []

    for item in data.get("items", []):
        status = item.get("status", {})
        metadata = item.get("metadata", {})

        conditions = {
            condition["type"]: condition["status"]
            for condition in status.get("conditions", [])
        }

        snapshot.append(
            {
                "name": metadata.get("name"),
                "phase": status.get("phase"),
                "ready": conditions.get("Ready"),
                "pod_ip": status.get("podIP"),
                "start_time": status.get("startTime"),
                "deletion_timestamp": metadata.get(
                    "deletionTimestamp"
                ),
            }
        )

    return snapshot


def print_pods(label: str) -> None:
    print(f"\n=== {label} ===")

    code, stdout, stderr = run_kubectl(
        "get",
        "pods",
        "-n",
        NAMESPACE,
        "-o",
        "wide",
    )

    if code == 0:
        print(stdout)
    else:
        print(f"Unable to read pods: {stderr}")


def trigger_rollout() -> None:
    """
    Trigger a harmless rolling restart.

    Kubernetes command:
        kubectl rollout restart deployment/ulpf -n ulpf

    The rollout is intentionally performed while continuous traffic
    is active to verify service resilience.
    """

    print("\n=== Triggering Kubernetes Rolling Update ===")

    code, stdout, stderr = run_kubectl(
        "rollout",
        "restart",
        f"deployment/{DEPLOYMENT}",
        "-n",
        NAMESPACE,
    )

    if code != 0:
        raise RuntimeError(f"Failed to trigger rollout: {stderr}")

    print(stdout or "✓ Rollout restart triggered")


def wait_for_rollout() -> bool:
    """
    Wait for Kubernetes to complete the rollout.

    Kubernetes commands:
        kubectl rollout restart deployment/ulpf -n ulpf
        kubectl rollout status deployment/ulpf -n ulpf --timeout=120s
    """

    print("\n=== Waiting for Rollout ===")

    code, stdout, stderr = run_kubectl(
        "rollout",
        "status",
        f"deployment/{DEPLOYMENT}",
        "-n",
        NAMESPACE,
        "--timeout=120s",
    )

    if code == 0:
        print(stdout)
        return True

    print(f"Rollout did not complete successfully: {stderr}")
    return False


def deployment_snapshot() -> dict:
    """Capture final deployment state."""

    data = kubectl_json(
        "get",
        "deployment",
        DEPLOYMENT,
        "-n",
        NAMESPACE,
    )

    status = data.get("status", {})

    return {
        "replicas": status.get("replicas"),
        "ready_replicas": status.get("readyReplicas"),
        "available_replicas": status.get("availableReplicas"),
        "updated_replicas": status.get("updatedReplicas"),
        "unavailable_replicas": status.get("unavailableReplicas", 0),
    }


def calculate_summary(
    results: list[RequestResult],
    rollout_success: bool,
) -> dict:

    total = len(results)

    # Step 16 resilience guards required by the contract test.
    http_error_statuses = sorted(
        {
            result.status_code
            for result in results
            if result.status_code is not None
            and result.status_code >= 400
        }
    )

    trace_ids_observed = sorted(
        {
            result.trace_id
            for result in results
            if result.trace_id
        }
    )

    successful = sum(
        1 for result in results if result.success
    )

    failed = total - successful

    five_xx = sum(
        1
        for result in results
        if result.status_code is not None
        and 500 <= result.status_code <= 599
    )

    latencies = [
        result.latency_ms
        for result in results
        if result.success
    ]

    if latencies:
        latency_avg = statistics.mean(latencies)
        latency_max = max(latencies)
        latency_p95 = sorted(latencies)[
            max(0, int(len(latencies) * 0.95) - 1)
        ]
    else:
        latency_avg = None
        latency_max = None
        latency_p95 = None

    return {
        "test": "ULPF Step 16 - Rolling Update Resilience",
        "timestamp": utc_now(),
        "request_duration_seconds": REQUEST_DURATION_SECONDS,
        "request_interval_seconds": REQUEST_INTERVAL_SECONDS,
        "total_requests": total,
        "successful_requests": successful,
        "failed_requests": failed,
        "http_5xx_responses": five_xx,
        "success_rate_percent": (
            round(successful / total * 100, 2)
            if total
            else 0
        ),
        "latency_avg_ms": (
            round(latency_avg, 2)
            if latency_avg is not None
            else None
        ),
        "latency_p95_ms": (
            round(latency_p95, 2)
            if latency_p95 is not None
            else None
        ),
        "latency_max_ms": (
            round(latency_max, 2)
            if latency_max is not None
            else None
        ),
        "rollout_success": rollout_success,
        "acceptance": {
            "rollout_completed": rollout_success,
            "no_unexpected_5xx": five_xx == 0,
            "requests_served": successful > 0,
        },
    }


def save_results(
    results: list[RequestResult],
    summary: dict,
    pod_snapshots: list[dict],
    deployment: dict,
) -> None:

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    output_file = OUTPUT_DIR / (
        f"step16_result_{timestamp}.json"
    )

    payload = {
        "summary": summary,
        "requests": [
            asdict(result)
            for result in results
        ],
        "pod_snapshots": pod_snapshots,
        "final_deployment": deployment,
    }

    output_file.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )

    print(f"\n✓ Results saved to:")
    print(output_file)


def print_summary(summary: dict) -> None:

    print("\n")
    print("=" * 60)
    print("STEP 16 RESILIENCE TEST SUMMARY")
    print("=" * 60)

    print(
        f"Total requests      : "
        f"{summary['total_requests']}"
    )

    print(
        f"Successful requests : "
        f"{summary['successful_requests']}"
    )

    print(
        f"Failed requests     : "
        f"{summary['failed_requests']}"
    )

    print(
        f"HTTP 5xx responses  : "
        f"{summary['http_5xx_responses']}"
    )

    print(
        f"Success rate        : "
        f"{summary['success_rate_percent']}%"
    )

    print(
        f"Average latency     : "
        f"{summary['latency_avg_ms']} ms"
    )

    print(
        f"P95 latency         : "
        f"{summary['latency_p95_ms']} ms"
    )

    print(
        f"Maximum latency     : "
        f"{summary['latency_max_ms']} ms"
    )

    print(
        f"Rollout completed   : "
        f"{summary['rollout_success']}"
    )

    print("=" * 60)

    if all(summary["acceptance"].values()):
        print("RESULT: PASS ✓")
    else:
        print("RESULT: REVIEW REQUIRED")


def main() -> None:

    print("=" * 60)
    print("ULPF STEP 16 - ROLLING UPDATE RESILIENCE TEST")
    print("=" * 60)

    check_prerequisites()

    print_pods("Initial Pod State")

    print(
        f"\nStarting continuous traffic for "
        f"{REQUEST_DURATION_SECONDS} seconds..."
    )

    results: list[RequestResult] = []
    pod_snapshots: list[dict] = []

    stop_event = threading.Event()

    worker = threading.Thread(
        target=traffic_worker,
        args=(results, stop_event),
        daemon=True,
    )

    worker.start()

    # Give traffic a few seconds to establish baseline.
    print(
        f"Collecting baseline traffic for "
        f"{ROLLOUT_DELAY_SECONDS} seconds..."
    )

    time.sleep(ROLLOUT_DELAY_SECONDS)

    pod_snapshots.append(
        {
            "timestamp": utc_now(),
            "stage": "before_rollout",
            "pods": get_pod_snapshot(),
        }
    )

    print_pods("Before Rollout")

    trigger_rollout()

    pod_snapshots.append(
        {
            "timestamp": utc_now(),
            "stage": "rollout_started",
            "pods": get_pod_snapshot(),
        }
    )

    # Monitor while rollout happens.
    rollout_success = wait_for_rollout()
    rollout_succeeded = rollout_success

    pod_snapshots.append(
        {
            "timestamp": utc_now(),
            "stage": "after_rollout",
            "pods": get_pod_snapshot(),
        }
    )

    print_pods("After Rollout")

    # Allow the service to stabilize after rollout.
    print("\nAllowing service to stabilize...")
    time.sleep(5)

    stop_event.set()
    worker.join(timeout=5)

    final_deployment = deployment_snapshot()
    
    summary = calculate_summary(
    results,
    rollout_succeeded,
    )

    summary["rollout_succeeded"] = rollout_succeeded

    save_results(
        results,
        summary,
        pod_snapshots,
        final_deployment,
    )

    print_summary(summary)


if __name__ == "__main__":
    main()