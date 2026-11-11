"""STK-099 read-only Linux/VPS resource inventory. No Docker or host mutations.

Exit 2 means NO-GO. A passing static budget is not load/restore acceptance.
Run on the VPS, or evaluate a captured JSON inventory in tests.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

MIB = 1024**2
# Compose hard limits 1376 MiB + 384 MiB OS reserve + 128 MiB emergency margin.
RUNTIME_BUDGET = 1888 * MIB


def assess(data):
    blockers = []
    for key, minimum in [('memory_total', RUNTIME_BUDGET), ('cpus', 2),
                         ('disk_free', max(6*1024**3, 3*data.get('database_bytes', 0)+2*1024**3))]:
        if data.get(key, 0) < minimum: blockers.append(key+'_insufficient')
    if data.get('memory_available', 0) < 768*MIB: blockers.append('available_memory_insufficient')
    if data.get('swap_used', 0) > 256*MIB: blockers.append('swap_pressure')
    if data.get('public_database_ports', True): blockers.append('database_public_or_unverified')
    if data.get('oom_kills', 0): blockers.append('container_oom_observed')
    return dict(static_budget='NO_GO' if blockers else 'PASS', blockers=blockers,
                deployment='NO_GO_until_restore_load_and_private_access_acceptance',
                proposed_runtime_limit_bytes=1376*MIB, inventory=data)


def collect(path):
    mem = {line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines()}
    containers = subprocess.check_output(['docker', 'ps', '-q'], text=True).split()
    inspected = json.loads(subprocess.check_output(['docker','inspect',*containers])) if containers else []
    ports = [binding for item in inspected for port, bindings in item['NetworkSettings']['Ports'].items()
             if port.startswith('5432/') for binding in bindings or []]
    return dict(memory_total=mem['MemTotal'], memory_available=mem['MemAvailable'],
                swap_total=mem['SwapTotal'], swap_used=mem['SwapTotal']-mem['SwapFree'],
                cpus=os.cpu_count(), disk_free=shutil.disk_usage(path).free,
                public_database_ports=any(p['HostIp'] not in ('127.0.0.1','::1') for p in ports),
                oom_kills=sum(bool(item['State']['OOMKilled']) for item in inspected),
                containers=[dict(name=item['Name'], image=item['Config']['Image'],
                                 memory_limit=item['HostConfig']['Memory']) for item in inspected])


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--inventory',type=Path)
    parser.add_argument('--path',default='/')
    parser.add_argument('--database-bytes',type=int,default=0,help='measured combined source/target database size for restore space budget')
    args=parser.parse_args()
    data=json.loads(args.inventory.read_text()) if args.inventory else collect(args.path)
    data['database_bytes']=max(data.get('database_bytes',0),args.database_bytes)
    result=assess(data)
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['static_budget']=='PASS' else 2)


if __name__=='__main__': main()
