import os
import threading
import time
import urllib.request
from datetime import datetime, timezone

TARGET_URL = os.getenv("TARGET_URL", "http://k8s-api:8000/telemetry/cluster-metrics")
WARMUP_SECONDS = float(os.getenv("WARMUP_SECONDS", "10"))
CONCURRENCY = int(os.getenv("CONCURRENCY", "10"))
REQUEST_TIMEOUT_S = float(os.getenv("REQUEST_TIMEOUT_S", "5.0"))


def ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def worker(worker_id: int):
    while True:
        try:
            with urllib.request.urlopen(TARGET_URL, timeout=REQUEST_TIMEOUT_S) as resp:
                resp.read()
        except Exception:
            pass


if __name__ == "__main__":
    print(f"[{ts()}] telemetry-agent waiting warmup={WARMUP_SECONDS}s", flush=True)
    time.sleep(WARMUP_SECONDS)
    print(f"[{ts()}] telemetry-agent STARTING flood concurrency={CONCURRENCY} target={TARGET_URL}", flush=True)
    threads = []
    for i in range(CONCURRENCY):
        t = threading.Thread(target=worker, args=(i,), daemon=True)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

