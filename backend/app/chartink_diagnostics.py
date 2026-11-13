"""Optional private ephemeral diagnostics, independent of database migrations."""
import fcntl
import json
import os
from pathlib import Path
from stock_discovery_analysis.chartink_diagnostics import payload_shape

FILE=Path('/tmp/chartink-rejection-shapes.json')
MAX_RECORDS=20


def enabled():return os.getenv('CHARTINK_REJECTION_DIAGNOSTICS')=='true'


def record(payload,reason):
    if not enabled():return
    # Called with a normalized reason code only; never an exception or raw body.
    summary={'reason':reason,**payload_shape(payload)}
    try:
        with open(str(FILE)+'.lock','a') as lock:
            os.chmod(lock.name,0o600)
            fcntl.flock(lock,fcntl.LOCK_EX)
            records=json.loads(FILE.read_text()) if FILE.exists() else []
            records=(records+[summary])[-MAX_RECORDS:]
            temp=FILE.with_suffix('.tmp')
            fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
            with os.fdopen(fd,'w') as out:json.dump(records,out,separators=(',',':'))
            temp.replace(FILE)
    except (OSError,ValueError,TypeError):
        # Diagnostics cannot change rejection handling or disclose exception values.
        return


def read():
    if not enabled():return {'enabled':False}
    try:
        return {'enabled':True,'records':json.loads(FILE.read_text()) if FILE.exists() else []}
    except (OSError,ValueError):return {'enabled':True,'available':False}
