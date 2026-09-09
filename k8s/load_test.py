"""Concurrent load test for the ULPF parse endpoint."""

import argparse
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


RAW_MESSAGE = (
    'date=2026-09-09 devname="FW01" srcip=10.0.0.5 '
    'dstip=192.168.1.20 action=deny'
)


def send_request(base_url: str, api_key: str, timeout: float) -> dict:
    payload = json.dumps({"message": RAW_MESSAGE}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    request = Request(f"{base_url.rstrip('/')}/parse", data=payload, headers=headers, method="POST")
    started = time.perf_counter()
    try:
        with urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
            return {
                "ok": response.status == 200 and body.get("accepted") is True,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "trace_id": response.headers.get("X-Trace-ID", ""),
                "status": response.status,
            }
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        return {
            "ok": False,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "trace_id": "",
            "status": getattr(error, "code", 0),
            "error": str(error),
        }


def run_load_test(base_url: str, requests: int, workers: int, api_key: str, timeout: float) -> dict:
    started = time.perf_counter()
    results = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(send_request, base_url, api_key, timeout) for _ in range(requests)]
        for future in as_completed(futures):
            results.append(future.result())

    latencies = [result["latency_ms"] for result in results]
    successful = [result for result in results if result["ok"]]
    summary = {
        "base_url": base_url,
        "requests": requests,
        "workers": workers,
        "successful": len(successful),
        "failed": requests - len(successful),
        "duration_seconds": round(time.perf_counter() - started, 3),
        "requests_per_second": round(requests / max(time.perf_counter() - started, 0.001), 2),
        "average_latency_ms": round(statistics.mean(latencies), 2) if latencies else 0,
        "maximum_latency_ms": max(latencies) if latencies else 0,
        "trace_ids_observed": len({result["trace_id"] for result in successful if result["trace_id"]}),
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:18000")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--api-key", default="")
    parser.add_argument("--timeout", type=float, default=10)
    args = parser.parse_args()
    if args.requests < 1 or args.workers < 1:
        parser.error("--requests and --workers must be positive")

    summary = run_load_test(args.base_url, args.requests, args.workers, args.api_key, args.timeout)
    print(json.dumps(summary, indent=2))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
