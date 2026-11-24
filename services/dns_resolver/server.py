import json
import os
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

PORT = int(os.getenv("PORT", "8053"))
K8S_API_URL = os.getenv("K8S_API_URL", "http://k8s-api:8000/endpoints/inference")
DNS_TTL_SECONDS = float(os.getenv("DNS_TTL_SECONDS", "12"))
UPSTREAM_TIMEOUT_S = float(os.getenv("UPSTREAM_TIMEOUT_S", "1.5"))
SERVE_STALE = os.getenv("SERVE_STALE", "false").lower() == "true"

cache_lock = threading.Lock()
dns_cache = {}


def ts() -> str:
    return datetime.now(timezone.utc).isoformat()


class DnsHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def _send_json(self, code: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/resolve":
            self._send_json(404, {"error": "not found"})
            return

        name = parse_qs(parsed.query).get("name", ["inference.svc.cluster.local"])[0]
        now = time.monotonic()

        with cache_lock:
            entry = dns_cache.get(name)
            if entry and now < entry["expires_at"]:
                ttl_left = round(entry["expires_at"] - now, 2)
                self._send_json(200, {"name": name, "ip": entry["ip"], "source": "cache", "ttl_left_s": ttl_left})
                return

        try:
            with urllib.request.urlopen(K8S_API_URL, timeout=UPSTREAM_TIMEOUT_S) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                ip = data["ip"]
                with cache_lock:
                    dns_cache[name] = {"ip": ip, "expires_at": time.monotonic() + DNS_TTL_SECONDS}
                print(f"[{ts()}] dns-resolver CACHE_REFRESH name={name} ip={ip} ttl={DNS_TTL_SECONDS}s", flush=True)
                self._send_json(200, {"name": name, "ip": ip, "source": "k8s-api", "ttl_left_s": DNS_TTL_SECONDS})
        except Exception as exc:
            with cache_lock:
                stale_entry = dns_cache.get(name)
            if SERVE_STALE and stale_entry:
                print(
                    f"[{ts()}] dns-resolver SERVE_STALE name={name} ip={stale_entry['ip']} reason={exc}",
                    flush=True,
                )
                self._send_json(
                    200,
                    {"name": name, "ip": stale_entry["ip"], "source": "stale-cache", "ttl_left_s": 0},
                )
                return
            print(f"[{ts()}] dns-resolver SERVFAIL name={name} reason={exc}", flush=True)
            self._send_json(503, {"name": name, "error": "SERVFAIL", "detail": str(exc)})


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), DnsHandler)
    print(f"[{ts()}] dns-resolver started port={PORT} ttl={DNS_TTL_SECONDS}s serve_stale={SERVE_STALE}", flush=True)
    server.serve_forever()

