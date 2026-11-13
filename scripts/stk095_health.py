"""STK-095: pure, privacy-safe external monitor decision; no network or sending.

A separately authorized monitor supplies authenticated observations. Missing
observations fail closed; empty event history never proves zero market matches.
"""
import argparse
import json
from pathlib import Path
import time


def codes(snapshot, now):
    result=[]
    def recent(key,seconds):
        value=snapshot.get(key)
        return type(value) in (int,float) and 0 <= now-value <= seconds
    if snapshot.get('receiver_healthy') is not True:result.append('receiver_unavailable')
    if not recent('observed_at',180):result.append('observation_stale')
    if not recent('consumer_completed_at',180):result.append('consumer_stale')
    if not recent('backup_restore_verified_at',26*3600):result.append('backup_unverified_or_stale')
    high,cursor=snapshot.get('high_water'),snapshot.get('cursor')
    if type(high) is not int or type(cursor) is not int or min(high,cursor)<0:
        result.append('cursor_observation_invalid')
    elif cursor>high:result.append('cursor_ahead_recovery_required')
    elif cursor<high:result.append('consumer_backlog')
    if snapshot.get('expected_alert_due') is True and not recent('last_receipt_at',30*60):
        result.append('expected_delivery_unverified')
    if snapshot.get('new_rejections',0)!=0:result.append('receiver_rejections')
    return sorted(result)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('snapshot',type=Path);a=p.parse_args()
    try:result=codes(json.loads(a.snapshot.read_text()),time.time())
    except Exception:result=['observation_invalid']
    print(json.dumps({'codes':result}));raise SystemExit(bool(result))
