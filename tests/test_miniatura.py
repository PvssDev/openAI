import json
import os
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def wait_http_ok(url: str, timeout_s: float = 5.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status == 200:
                    return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError(f"Service at {url} did not become ready in {timeout_s}s")


class TestMiniaturaFlow(unittest.TestCase):
    def setUp(self):
        self.procs = []
        self.api_port = 18000
        self.dns_port = 18053

        api_env = os.environ.copy()
        api_env.update({
            "PORT": str(self.api_port),
            "MAX_WORKERS": "2",
            "MAX_QUEUE": "2",
            "HEAVY_OP_DELAY_MS": "1200",
        })
        self.api_proc = subprocess.Popen(
            [sys.executable, "-u", str(ROOT / "services" / "k8s_api" / "server.py")],
            env=api_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.procs.append(self.api_proc)
        wait_http_ok(f"http://127.0.0.1:{self.api_port}/healthz")

        dns_env = os.environ.copy()
        dns_env.update({
            "PORT": str(self.dns_port),
            "K8S_API_URL": f"http://127.0.0.1:{self.api_port}/endpoints/inference",
            "DNS_TTL_SECONDS": "3",
            "UPSTREAM_TIMEOUT_S": "1.0",
        })
        self.dns_proc = subprocess.Popen(
            [sys.executable, "-u", str(ROOT / "services" / "dns_resolver" / "server.py")],
            env=dns_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.procs.append(self.dns_proc)
        wait_http_ok(f"http://127.0.0.1:{self.dns_port}/resolve?name=inference.svc.cluster.local")

    def tearDown(self):
        for proc in self.procs:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()

    def _resolve(self):
        url = f"http://127.0.0.1:{self.dns_port}/resolve?name=inference.svc.cluster.local"
        with urllib.request.urlopen(url, timeout=2.0) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))

    def test_cache_masks_overload_then_fails_and_recovers(self):
        # 1. Cache was populated in setUp -> immediate request must come from cache
        status, data = self._resolve()
        self.assertEqual(status, 200)
        self.assertEqual(data["source"], "cache")

        # 2. Start telemetry flood immediately (warmup=0)
        tel_env = os.environ.copy()
        tel_env.update({
            "TARGET_URL": f"http://127.0.0.1:{self.api_port}/telemetry/cluster-metrics",
            "WARMUP_SECONDS": "0",
            "CONCURRENCY": "8",
            "REQUEST_TIMEOUT_S": "3.0",
        })
        tel_proc = subprocess.Popen(
            [sys.executable, "-u", str(ROOT / "services" / "telemetry_agent" / "agent.py")],
            env=tel_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.procs.append(tel_proc)

        # Give flood a moment to saturate k8s-api while TTL is still valid
        time.sleep(0.6)
        status, data = self._resolve()
        self.assertEqual(status, 200)
        self.assertEqual(data["source"], "cache")

        # 3. Wait for TTL (3s) to expire -> DNS resolution must fail with 503 SERVFAIL
        time.sleep(3.0)
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._resolve()
        self.assertEqual(ctx.exception.code, 503)
        ctx.exception.close()

        # 4. Stop telemetry flood (rollback) -> system must recover
        tel_proc.terminate()
        tel_proc.wait(timeout=3)

        recovered = False
        for _ in range(15):
            try:
                status, data = self._resolve()
                if status == 200 and data["source"] == "k8s-api":
                    recovered = True
                    break
            except Exception:
                time.sleep(0.3)
        self.assertTrue(recovered, "dns-resolver did not recover after stopping telemetry-agent")

    def test_mitigation_serve_stale_prevents_dns_outage(self):
        # Start a second dns-resolver instance with SERVE_STALE=true
        mitigated_dns_port = 18054
        dns_env = os.environ.copy()
        dns_env.update({
            "PORT": str(mitigated_dns_port),
            "K8S_API_URL": f"http://127.0.0.1:{self.api_port}/endpoints/inference",
            "DNS_TTL_SECONDS": "2",
            "UPSTREAM_TIMEOUT_S": "1.0",
            "SERVE_STALE": "true",
        })
        mitigated_dns = subprocess.Popen(
            [sys.executable, "-u", str(ROOT / "services" / "dns_resolver" / "server.py")],
            env=dns_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.procs.append(mitigated_dns)
        url = f"http://127.0.0.1:{mitigated_dns_port}/resolve?name=inference.svc.cluster.local"
        wait_http_ok(url)

        # Saturate k8s-api aggressively
        tel_env = os.environ.copy()
        tel_env.update({
            "TARGET_URL": f"http://127.0.0.1:{self.api_port}/telemetry/cluster-metrics",
            "WARMUP_SECONDS": "0",
            "CONCURRENCY": "8",
            "REQUEST_TIMEOUT_S": "3.0",
        })
        tel_proc = subprocess.Popen(
            [sys.executable, "-u", str(ROOT / "services" / "telemetry_agent" / "agent.py")],
            env=tel_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.procs.append(tel_proc)

        # Wait for TTL (2s) to expire while k8s-api is saturated
        time.sleep(2.5)
        with urllib.request.urlopen(url, timeout=2.0) as resp:
            status = resp.status
            data = json.loads(resp.read().decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertIn(data["source"], ("stale-cache", "k8s-api"))


if __name__ == "__main__":
    unittest.main()
