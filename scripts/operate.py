"""Private-host backup/monitor entrypoint. Does not provision or initialize B2."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import shutil
import time
from backup_restore import COMPOSE, backup, command, verify_restore


def run(args, **kwargs):
    # Never print subprocess arguments, stderr, repository URLs or credentials.
    return subprocess.run(args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs).stdout


def restic(*args):
    return run([os.environ.get("RESTIC_BINARY", "restic"), *args])


def save(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, sort_keys=True) + "\n")
    temp.chmod(0o600)
    temp.replace(path)


def notify(event, codes):
    # Only an explicitly configured local executable is invoked. No shell,
    # external message or notification destination is selected automatically.
    payload = json.dumps({"event": event, "codes": sorted(codes)})
    print(payload, flush=True)
    hook = os.getenv("STK_ALERT_EXECUTABLE")
    if hook:
        run([hook], input=payload.encode())


def backup_cycle(state):
    if not os.getenv("RESTIC_REPOSITORY") or not os.getenv("RESTIC_PASSWORD_FILE"):
        raise ValueError("Explicit initialized restic repository and password file required")
    for name in ("RESTIC_PASSWORD_FILE",):
        p = Path(os.environ[name])
        if p.stat().st_mode & 0o077:
            raise ValueError("Backup key file must be owner-only")
    # Stable directory/path makes restic retention grouping deterministic.
    stage = state / "stage"
    stage.mkdir(mode=0o700, exist_ok=True)
    dump = stage / "database.dump"
    manifest = stage / "manifest.json"
    if dump.exists() or manifest.exists():
        raise ValueError("Previous staging artifacts need operator review")
    restart = False
    try:
        restart = True
        run([*COMPOSE, "stop", "api", "worker"])
        evidence = backup(dump, verify=True)
        evidence.update(at=time.time(), code_version=os.environ["CODE_VERSION"], size_bytes=dump.stat().st_size)
        containers = run([*COMPOSE, "ps", "--all", "-q"]).decode().splitlines()
        evidence["images"] = [run(["docker", "inspect", "--format", "{{.Image}}", cid]).decode().strip() for cid in containers]
        bundle = os.getenv("STK_RECOVERY_BUNDLE")
        if bundle:
            shutil.copyfile(bundle, stage / "recovery.bundle")
            (stage / "recovery.bundle").chmod(0o600)
        evidence["configuration_bundle_included"] = bool(bundle)
        save(manifest, evidence)
    finally:
        if restart:
            run([*COMPOSE, "start", "api", "worker"])
    try:
        output = restic("backup", "--json", "--tag", "stock-discovery", str(stage))
        summaries = [json.loads(line) for line in output.splitlines()]
        snapshot = next(row["snapshot_id"] for row in summaries if row.get("message_type") == "summary")
        # Download/decrypt this exact snapshot, not 'latest'; compare and restore it.
        with tempfile.TemporaryDirectory(dir=state) as recovered:
            restic("restore", snapshot, "--target", recovered)
            restored = Path(recovered) / stage.relative_to(stage.anchor)
            saved = json.loads((restored / "manifest.json").read_text())
            with (restored / "database.dump").open("rb") as source:
                if hashlib.file_digest(source, "sha256").hexdigest() != saved["sha256"]:
                    raise ValueError("Recovered dump checksum differs")
            schema = verify_restore(restored / "database.dump", saved["research_tables"])
            if schema != saved["schema"]:
                raise ValueError("Recovered schema differs")
        # The VPS backup identity must not have pruning credentials.
        # Retention is a separate owner-controlled operation after verification.
        save(state / "last-backup.json", {**evidence, "snapshot": snapshot, "verified_at": time.time()})
        notify("backup_verified", [])
    finally:
        # These are only files created by this invocation, inside private staging.
        dump.unlink(missing_ok=True)
        manifest.unlink(missing_ok=True)
        (stage / "recovery.bundle").unlink(missing_ok=True)


def prune(state):
    if os.getenv("STK_PRUNE_AUTHORIZED") != "true":
        raise ValueError("Retention requires explicit offline-owner authorization")
    receipt = json.loads((state / "last-backup.json").read_text())
    if not 0 <= time.time() - receipt["verified_at"] <= 26 * 3600:
        raise ValueError("A recent verified recovery receipt is required")
    snapshots = json.loads(restic("snapshots", "--json", receipt["snapshot"]))
    if not snapshots or not any(row["id"].startswith(receipt["snapshot"]) for row in snapshots):
        raise ValueError("Verified snapshot is absent from repository")
    restic("check", "--read-data")
    restic("forget", "--tag", "stock-discovery", "--group-by", "host,paths,tags",
           "--keep-daily", "7", "--keep-weekly", "4", "--keep-monthly", "3", "--prune")


def monitor(state):
    codes = []
    raw = run([*COMPOSE, "ps", "--all", "--format", "json"]).decode()
    rows = json.loads(raw) if raw.lstrip().startswith("[") else [json.loads(line) for line in raw.splitlines() if line.strip()]
    if isinstance(rows, dict): rows = [rows]
    services = {row["Service"]: row for row in rows}
    for service in ("database", "api", "worker", "web"):
        row = services.get(service, {})
        if row.get("State") != "running" or row.get("Health") == "unhealthy":
            codes.append(service + "_unavailable")
    stats = os.statvfs(state)
    if stats.f_bavail / max(stats.f_blocks, 1) < 0.25:
        codes.append("disk_below_25_percent")
    try:
        saved = json.loads((state / "last-backup.json").read_text())
        if time.time() - saved["verified_at"] > 26 * 3600:
            codes.append("backup_stale")
    except (OSError, ValueError, KeyError):
        codes.append("backup_unverified")
    try:
        sql = b"SELECT count(*) FILTER (WHERE status='failed'), count(*) FILTER (WHERE (status='queued' AND created_at<now()-interval '15 minutes') OR (status='running' AND lease_until<now())) FROM research.jobs;"
        values = command('psql -X -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -v ON_ERROR_STOP=1', input=sql).decode().strip().split("|")
        if int(values[0]): codes.append("jobs_failed")
        if int(values[1]): codes.append("jobs_stale")
    except Exception:
        codes.append("queue_check_failed")
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        memory = dict((line.split(":")[0], int(line.split()[1])) for line in meminfo.read_text().splitlines())
        if memory.get("MemAvailable", 0) / max(memory.get("MemTotal", 1), 1) < 0.10:
            codes.append("memory_below_10_percent")
    if os.getenv("APP_ORIGIN"):
        import ssl
        import socket
        from urllib.parse import urlsplit
        try:
            host = urlsplit(os.environ["APP_ORIGIN"]).hostname
            with socket.create_connection((host, 443), timeout=5) as sock:
                with ssl.create_default_context().wrap_socket(sock, server_hostname=host) as tls:
                    if ssl.cert_time_to_seconds(tls.getpeercert()["notAfter"]) - time.time() < 14 * 86400:
                        codes.append("certificate_near_expiry")
        except Exception:
            codes.append("private_https_unavailable")
    previous = state / "monitor.json"
    try: old = json.loads(previous.read_text())["codes"]
    except (OSError, ValueError, KeyError): old = None
    if old != sorted(codes):
        notify("monitor_changed", codes)
    save(previous, {"at": time.time(), "codes": sorted(codes)})
    return not codes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("backup", "monitor", "check", "prune"))
    args = parser.parse_args()
    os.umask(0o077)
    state = Path(os.environ.get("STK_STATE_DIR", "/var/lib/stock-discovery-ops"))
    state.mkdir(parents=True, mode=0o700, exist_ok=True)
    if state.stat().st_mode & 0o077:
        raise SystemExit("Operations state directory must be owner-only")
    with (state / "lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            # The nightly backup intentionally stops writers; avoid false alarms.
            if args.action == "monitor": return 0
            notify("operation_failed", ["operation_already_running"])
            return 1
        try:
            if args.action == "backup": backup_cycle(state)
            elif args.action == "check": restic("check", "--read-data")
            elif args.action == "prune": prune(state)
            elif not monitor(state): return 1
        except Exception:
            notify("operation_failed", [args.action + "_failed"])
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
