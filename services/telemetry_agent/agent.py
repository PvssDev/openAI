import os
import random
import threading
import time
import urllib.request
from datetime import datetime, timezone

TARGET_URL = os.getenv("TARGET_URL", "http://k8s-api:8000/telemetry/cluster-metrics")
WARMUP_SECONDS = float(os.getenv("WARMUP_SECONDS", "10"))
CONCURRENCY = int(os.getenv("CONCURRENCY", "10"))
REQUEST_TIMEOUT_S = float(os.getenv("REQUEST_TIMEOUT_S", "5.0"))
BACKOFF_JITTER = os.getenv("BACKOFF_JITTER", "false").lower() == "true"
BASE_BACKOFF_S = float(os.getenv("BASE_BACKOFF_S", "0.5"))
MAX_BACKOFF_S = float(os.getenv("MAX_BACKOFF_S", "8.0"))


def ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def worker(worker_id: int):
    consecutive_errors = 0
    while True:
        try:
            with urllib.request.urlopen(TARGET_URL, timeout=REQUEST_TIMEOUT_S) as resp:
                resp.read()
            consecutive_errors = 0
            if BACKOFF_JITTER:
                # Espaça coletas mesmo em sucesso para evitar rajada contínua
                time.sleep(BASE_BACKOFF_S + random.uniform(0, BASE_BACKOFF_S))
        except Exception:
            if BACKOFF_JITTER:
                consecutive_errors += 1
                delay = min(MAX_BACKOFF_S, BASE_BACKOFF_S * (2 ** min(consecutive_errors, 4)))
                jittered = random.uniform(delay * 0.5, delay)
                time.sleep(jittered)


if __name__ == "__main__":
    print(
        f"[{ts()}] telemetry-agent waiting warmup={WARMUP_SECONDS}s backoff_jitter={BACKOFF_JITTER}",
        flush=True,
    )
    time.sleep(WARMUP_SECONDS)
    print(
        f"[{ts()}] telemetry-agent STARTING flood concurrency={CONCURRENCY} target={TARGET_URL} backoff_jitter={BACKOFF_JITTER}",
        flush=True,
    )
    threads = []
    for i in range(CONCURRENCY):
        t = threading.Thread(target=worker, args=(i,), daemon=True)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
