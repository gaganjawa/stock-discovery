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
    if os.getenv("STK099_TRANSFER_CONFIG"):
        return transfer_backup_cycle(state)
    if os.getenv("STK_MONITOR_MODE") in ("receiver", "hosted"):
        raise ValueError("online_transfer_config_required")
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


def transfer_backup_cycle(state):
    """STK-099 online backup, using the existing full-schema transfer verifier.

    Recovery target must be an independently identified disposable cluster with
    the required roles already provisioned. No service stop/start or live DDL.
    """
    from stk099_transfer import Database, backup_online, checksum, identifier, restore
    import re
    from uuid import uuid4
    config_path = Path(os.environ['STK099_TRANSFER_CONFIG'])
    key = Path(os.environ['RESTIC_PASSWORD_FILE'])
    for path in (config_path, key):
        if not path.is_file() or path.is_symlink() or path.stat().st_mode & 0o077:
            raise ValueError('private_backup_file_required')
    repository = os.environ.get('RESTIC_REPOSITORY', '')
    if not repository.startswith(('b2:', 's3:https://', 'sftp:', 'rest:https://')):
        raise ValueError('remote_encrypted_repository_required')
    config = json.loads(config_path.read_text())
    if config.get('off_server_confirmed') is not True or config.get('separate_key_custody_confirmed') is not True:
        raise ValueError('destination_and_key_custody_confirmation_required')
    repository_id = config['repository_id']
    if not re.fullmatch('[0-9a-f]{64}', repository_id):
        raise ValueError('exact_repository_identity_required')
    if json.loads(restic('--no-cache', 'cat', 'config'))['id'] != repository_id:
        raise ValueError('repository_identity_mismatch')
    sources = config['sources']
    expected = {'receiver': {'chartink_inbox'}, 'hosted': {'chartink_inbox', 'stk_real001_private'}}
    if config.get('scope') not in expected or {x['database'] for x in sources} != expected[config['scope']] or len(sources) != len(expected[config['scope']]):
        raise ValueError('backup_scope_mismatch')
    recovery = config['recovery']
    target = Database(recovery['container'], recovery['owner'], 'postgres')
    target_cluster = target.sql('SELECT system_identifier FROM pg_control_system()')
    if target_cluster != recovery['cluster'] or target_cluster in {x['cluster'] for x in sources}:
        raise ValueError('recovery_cluster_must_be_independent')
    bundle = Path(os.environ['STK_RECOVERY_BUNDLE'])
    if not bundle.is_file() or bundle.is_symlink() or bundle.stat().st_mode & 0o077:
        raise ValueError('private_recovery_bundle_required')
    if config['bundle_sha256'] != checksum(bundle):
        raise ValueError('reviewed_recovery_bundle_changed')
    stage = state / 'stage'
    stage.mkdir(mode=0o700, exist_ok=True)
    if any(stage.iterdir()):
        raise ValueError('previous_backup_stage_requires_review')
    records = []
    for source in sources:
        name = identifier(source['database'])
        db = Database(source['container'], source['owner'], name)
        manifest = backup_online(db, stage / (name + '.dump'), source['cluster'])
        if manifest['snapshot']['revision'] != '0018':
            raise ValueError('schema_0018_required')
        records.append(dict(database=name, cluster=source['cluster'], restore_owner=source['restore_owner']))
        # Globals are recovery material only, never automatically executed.
        with (stage / (name + '.roles.sql')).open('xb') as out:
            db.run(['pg_dumpall', '-U', db.owner, '--roles-only'], stdout=out)
    shutil.copyfile(bundle, stage / 'recovery.bundle')
    (stage / 'recovery.bundle').chmod(0o600)
    if checksum(stage / 'recovery.bundle') != config['bundle_sha256'] or checksum(bundle) != config['bundle_sha256']:
        raise ValueError('recovery_bundle_changed_during_copy')
    for path in stage.iterdir():
        path.chmod(0o600)
    files = {path.name: checksum(path) for path in stage.iterdir() if path.is_file()}
    evidence = dict(at=time.time(), code_version=os.environ['CODE_VERSION'], scope=config['scope'],
                    schema='0018', databases=records, files=files, repository_id=repository_id)
    save(stage / 'manifest.json', evidence)
    summaries = [json.loads(line) for line in restic('backup', '--json', '--tag', 'stock-discovery', str(stage)).splitlines()]
    snapshot = next(row['snapshot_id'] for row in summaries if row.get('message_type') == 'summary')
    if not re.fullmatch('[0-9a-f]{8,64}', snapshot):
        raise ValueError('invalid_snapshot_identity')
    recovery_databases = []
    with tempfile.TemporaryDirectory(dir=state) as downloaded:
        restic('--no-cache', 'restore', snapshot, '--target', downloaded)
        restored = Path(downloaded) / stage.relative_to(stage.anchor)
        if json.loads((restored / 'manifest.json').read_text()) != evidence:
            raise ValueError('recovered_manifest_mismatch')
        for name, digest in files.items():
            if checksum(restored / name) != digest:
                raise ValueError('recovered_file_mismatch')
        for source in records:
            name = source['database']
            manifest = json.loads((restored / (name + '.manifest.json')).read_text())
            target_name = 'stk099_recovery_' + uuid4().hex[:12]
            restore(Database(recovery['container'], recovery['owner'], target_name),
                    restored / (name + '.dump'), manifest, source['restore_owner'],
                    expected_source=name, expected_source_cluster=source['cluster'])
            recovery_databases.append(dict(source=name, target=target_name, cluster=target_cluster))
        # Sources and recovery copies are retained; no drop, prune or migration.
    save(state / 'last-backup.json', {**evidence, 'snapshot': snapshot, 'verified_at': time.time(), 'recovery_databases': recovery_databases})
    for path in stage.iterdir():
        path.unlink()  # Only this successful cycle's files; failures retain evidence.
    notify('backup_verified', [])


def alert_test(state):
    hook = os.getenv('STK_ALERT_EXECUTABLE')
    if not hook or not Path(hook).is_file() or not os.access(hook, os.X_OK):
        raise ValueError('external_alert_hook_required')
    notify('release_alert_test', ['synthetic_delivery_drill'])
    save(state / 'last-alert-test.json', {'hook_accepted_at': time.time(), 'external_delivery_verified': False})
    # Transport success alone cannot assert recipient delivery.


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
    mode = os.getenv('STK_MONITOR_MODE', 'legacy')
    expected = {'legacy': ('database', 'api', 'worker', 'web'),
                'receiver': ('database', 'receiver', 'proxy'),
                'hosted': ('database', 'receiver', 'proxy', 'api', 'worker', 'web', 'price-refresh')}
    if mode not in expected:
        raise ValueError('unknown_monitor_mode')
    if not os.getenv('STK_ALERT_EXECUTABLE'):
        codes.append('external_alert_unconfigured')
    for service in expected[mode]:
        row = services.get(service, {})
        if row.get("State") != "running" or row.get("Health") in ("unhealthy", "starting"):
            codes.append(service + "_unavailable")
    stats = os.statvfs(state)
    if stats.f_bavail / max(stats.f_blocks, 1) < 0.25:
        codes.append("disk_below_25_percent")
    try:
        saved = json.loads((state / "last-backup.json").read_text())
        if mode != "legacy" and saved.get("scope") != mode:
            codes.append("backup_scope_mismatch")
        if not 0 <= time.time() - saved["verified_at"] <= 26 * 3600:
            codes.append("backup_stale")
    except (OSError, ValueError, KeyError):
        codes.append("backup_unverified")
    try:
        if mode == 'receiver':
            version = command('psql -X -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -v ON_ERROR_STOP=1',
                              input=b'SELECT version_num FROM public.alembic_version;').decode().strip()
            if version != '0018': codes.append('receiver_schema_unexpected')
        else:
            database = 'stk_real001_private' if mode == 'hosted' else ''
            queries = [("research.jobs", "(status='queued' AND created_at<now()-interval '15 minutes') OR (status='running' AND lease_until<now())")]
            if mode == 'hosted':
                queries.append(("discovery.schedule_jobs", "(status IN ('queued','retry_wait') AND due_at<now()-interval '15 minutes') OR (status='running' AND lease_until<now())"))
            for table, stale in queries:
                sql = f"SELECT count(*) FILTER (WHERE status='failed'), count(*) FILTER (WHERE {stale}) FROM {table};".encode()
                values = command('psql -X -U "$POSTGRES_USER" -d "${1:-$POSTGRES_DB}" -At -v ON_ERROR_STOP=1', database, input=sql).decode().strip().split('|')
                if int(values[0]): codes.append('jobs_failed')
                if int(values[1]): codes.append('jobs_stale')
    except Exception:
        codes.append('queue_check_failed')
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
    parser.add_argument("action", choices=("backup", "monitor", "check", "prune", "alert-test"))
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
            # Avoid overlapping checks with the serialized backup/verification cycle.
            if args.action == "monitor": return 0
            notify("operation_failed", ["operation_already_running"])
            return 1
        try:
            if args.action == "backup": backup_cycle(state)
            elif args.action == "alert-test": alert_test(state)
            elif args.action == "check": restic("check", "--read-data")
            elif args.action == "prune": prune(state)
            elif not monitor(state): return 1
        except Exception:
            notify("operation_failed", [args.action + "_failed"])
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
