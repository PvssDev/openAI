import json
import os
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.getenv("PORT", "8000"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))
MAX_QUEUE = int(os.getenv("MAX_QUEUE", "8"))
HEAVY_OP_DELAY_S = int(os.getenv("HEAVY_OP_DELAY_MS", "1500")) / 1000.0

worker_semaphore = threading.BoundedSemaphore(MAX_WORKERS)
queue_lock = threading.Lock()
in_flight = 0


def ts() -> str:
    return datetime.now(timezone.utc).isoformat()


class K8sApiHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return  # Suppress default stderr logging for structured output

    def _send_json(self, code: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        try:
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        global in_flight

        if self.path == "/healthz":
            self._send_json(200, {"status": "ok"})
            return

        overloaded = False
        current_in_flight = 0
        with queue_lock:
            if in_flight >= MAX_WORKERS + MAX_QUEUE:
                overloaded = True
                current_in_flight = in_flight
            else:
                in_flight += 1

        if overloaded:
            print(f"[{ts()}] k8s-api 503 OVERLOADED path={self.path} in_flight={current_in_flight}", flush=True)
            self._send_json(503, {"error": "kube-apiserver overloaded"})
            return

        acquired = worker_semaphore.acquire(timeout=1.0)
        if not acquired:
            with queue_lock:
                in_flight -= 1
            print(f"[{ts()}] k8s-api 503 TIMEOUT_QUEUE path={self.path}", flush=True)
            self._send_json(503, {"error": "kube-apiserver worker pool saturated"})
            return

        try:
            if self.path == "/telemetry/cluster-metrics":
                time.sleep(HEAVY_OP_DELAY_S)
                self._send_json(200, {"metrics": "ok", "cost": "heavy"})
            elif self.path == "/endpoints/inference":
                time.sleep(0.02)
                self._send_json(200, {"service": "inference", "ip": "10.0.0.42", "port": 8080})
            else:
                self._send_json(404, {"error": "not found"})
        finally:
            worker_semaphore.release()
            with queue_lock:
                in_flight -= 1


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), K8sApiHandler)
    print(f"[{ts()}] k8s-api started port={PORT} max_workers={MAX_WORKERS} max_queue={MAX_QUEUE}", flush=True)
    server.serve_forever()

