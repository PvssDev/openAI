import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT / "logs"


def ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def container_ts(compose_cmd: list[str]) -> str:
    res = run_cmd(
        compose_cmd
        + [
            "exec",
            "-T",
            "k8s-api",
            "python",
            "-c",
            "from datetime import datetime, timezone; print(datetime.now(timezone.utc).isoformat())",
        ],
        capture=True,
    )
    if res.returncode == 0 and res.stdout.strip():
        return res.stdout.strip().splitlines()[-1].strip()
    return ts()


def run_cmd(cmd: list[str], capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=capture, check=False)


def parse_metrics(prefix: str, flood_start_ts: str | None, rollback_ts: str | None):
    wc_log = (LOGS_DIR / f"{prefix}-workload-client.log").read_text(encoding="utf-8", errors="replace")
    tel_log = (LOGS_DIR / f"{prefix}-telemetry-agent.log").read_text(encoding="utf-8", errors="replace")

    tel_match = re.search(r"\[([^\]]+)\]\s+telemetry-agent STARTING flood", tel_log)
    if tel_match:
        flood_start_ts = tel_match.group(1)

    req_pattern = re.compile(
        r"\[([^\]]+)\]\s+t=([0-9.]+)s\s+req=(\d+)\s+status=(\S+)\s+source=(\S+)"
    )

    total = 0
    errors = 0
    first_error_ts = None
    first_error_req = None
    first_recovery_ts = None
    first_recovery_req = None
    saw_error = False

    for line in wc_log.splitlines():
        m = req_pattern.search(line)
        if not m:
            continue
        line_ts, _elapsed, req_num, status, _source = m.groups()
        total += 1
        is_err = status != "200"
        if is_err:
            errors += 1
            if not saw_error:
                saw_error = True
                first_error_ts = line_ts
                first_error_req = req_num
        elif saw_error and rollback_ts and line_ts >= rollback_ts and first_recovery_ts is None:
            first_recovery_ts = line_ts
            first_recovery_req = req_num

    def diff_s(t1: str | None, t2: str | None):
        if not t1 or not t2:
            return None
        dt1 = datetime.fromisoformat(t1)
        dt2 = datetime.fromisoformat(t2)
        return round((dt2 - dt1).total_seconds(), 2)

    error_rate = round((errors / total) * 100, 2) if total else 0.0
    summary = {
        "prefix": prefix,
        "total_requests": total,
        "error_requests": errors,
        "error_rate_pct": error_rate,
        "flood_start_ts": flood_start_ts,
        "first_error_ts": first_error_ts,
        "first_error_req": first_error_req,
        "time_to_failure_s": diff_s(flood_start_ts, first_error_ts),
        "rollback_ts": rollback_ts,
        "first_recovery_ts": first_recovery_ts,
        "first_recovery_req": first_recovery_req,
        "time_to_recovery_s": diff_s(rollback_ts, first_recovery_ts),
    }

    summary_lines = [f"{k}={v}" for k, v in summary.items()]
    (LOGS_DIR / f"{prefix}-resumo.txt").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    print("\n=== RESUMO EXTRAIDO DOS LOGS ===")
    print("\n".join(summary_lines))


def main():
    prefix = sys.argv[1] if len(sys.argv) > 1 else "sem-mitigacao"
    failure_window_s = int(sys.argv[2]) if len(sys.argv) > 2 else 36
    recovery_window_s = int(sys.argv[3]) if len(sys.argv) > 3 else 15

    use_mitigation = prefix == "com-mitigacao" or "--mitigado" in sys.argv
    compose_cmd = ["docker", "compose", "-f", "docker-compose.yml"]
    if use_mitigation:
        compose_cmd += ["-f", "docker-compose.mitigado.yml"]

    LOGS_DIR.mkdir(exist_ok=True)

    check = run_cmd(["docker", "info"], capture=True)
    if check.returncode != 0:
        print("ERRO: Docker daemon nao esta ativo. Abra o Docker Desktop e execute novamente.")
        sys.exit(1)

    print(f"[{ts()}] Limpando execucao anterior...")
    run_cmd(compose_cmd + ["down", "--remove-orphans"])

    print(f"[{ts()}] Subindo miniatura ({'COM mitigacao' if use_mitigation else 'SEM mitigacao'})...")
    up = run_cmd(compose_cmd + ["up", "-d"])
    if up.returncode != 0:
        sys.exit(up.returncode)

    try:
        print(f"[{ts()}] Aguardando {failure_window_s}s (warmup + mascaramento por cache + janela de carga)...")
        time.sleep(failure_window_s)

        rollback_ts = container_ts(compose_cmd)
        print(f"[{rollback_ts}] Executando rollback simulado: stop telemetry-agent")
        run_cmd(compose_cmd + ["stop", "telemetry-agent"])

        print(f"[{ts()}] Aguardando {recovery_window_s}s para observar recuperacao...")
        time.sleep(recovery_window_s)

        print(f"[{ts()}] Coletando logs brutos em logs/{prefix}-*.log...")
        all_logs = run_cmd(compose_cmd + ["logs", "--no-color"], capture=True)
        (LOGS_DIR / f"{prefix}-all.log").write_text(all_logs.stdout, encoding="utf-8")

        for svc in ["k8s-api", "dns-resolver", "telemetry-agent", "workload-client"]:
            res = run_cmd(compose_cmd + ["logs", "--no-color", svc], capture=True)
            (LOGS_DIR / f"{prefix}-{svc}.log").write_text(res.stdout, encoding="utf-8")

        parse_metrics(prefix, None, rollback_ts)
    finally:
        print(f"[{ts()}] Encerrando containers (docker compose down)...")
        run_cmd(compose_cmd + ["down"])


if __name__ == "__main__":
    main()

