import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

DNS_URL = os.getenv("DNS_URL", "http://dns-resolver:8053/resolve?name=inference.svc.cluster.local")
INTERVAL_S = int(os.getenv("INTERVAL_MS", "500")) / 1000.0
REQUEST_TIMEOUT_S = float(os.getenv("REQUEST_TIMEOUT_S", "2.0"))


def ts() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    start = time.monotonic()
    total = 0
    errors = 0
    print(f"[{ts()}] workload-client started dns_url={DNS_URL} interval={INTERVAL_S}s", flush=True)

    while True:
        req_start = time.monotonic()
        elapsed = round(req_start - start, 2)
        total += 1
        try:
            with urllib.request.urlopen(DNS_URL, timeout=REQUEST_TIMEOUT_S) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                latency_ms = round((time.monotonic() - req_start) * 1000, 1)
                print(
                    f"[{ts()}] t={elapsed}s req={total} status=200 source={data.get('source')} "
                    f"ttl_left={data.get('ttl_left_s')}s latency_ms={latency_ms} errors={errors}",
                    flush=True,
                )
        except urllib.error.HTTPError as exc:
            errors += 1
            latency_ms = round((time.monotonic() - req_start) * 1000, 1)
            print(
                f"[{ts()}] t={elapsed}s req={total} status={exc.code} source=error "
                f"latency_ms={latency_ms} errors={errors}",
                flush=True,
            )
        except Exception as exc:
            errors += 1
            latency_ms = round((time.monotonic() - req_start) * 1000, 1)
            print(
                f"[{ts()}] t={elapsed}s req={total} status=ERR source=timeout "
                f"latency_ms={latency_ms} errors={errors} detail={exc}",
                flush=True,
            )
        time.sleep(INTERVAL_S)

