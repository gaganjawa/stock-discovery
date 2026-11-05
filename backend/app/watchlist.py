"""Private owner metadata, separate from immutable market evidence."""
import fcntl
import json
import os
import tempfile
from pathlib import Path
from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from fastapi import HTTPException

class Entry(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: Literal['Researching', 'Monitoring', 'Not interested'] = 'Researching'
    note: str = Field(default='', max_length=2000)
    review_date: date | None = None


def store(listing=None, entry=None, remove=False, reviewed_observation=None):
    root = Path(os.environ.get('REAL_WATCHLIST_DIR', 'backups/private-watchlist'))
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if root.is_symlink() or root.stat().st_mode & 0o077:
        raise HTTPException(503, 'Watchlist directory must be private (0700)')
    path = root / 'watchlist.json'
    with os.fdopen(os.open(root / 'lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600), 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = {}
        if path.exists():
            if path.is_symlink() or path.stat().st_mode & 0o077:
                raise HTTPException(503, 'Watchlist file must be private (0600)')
            with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW)) as source:
                data = json.load(source)
        if listing is not None:
            if remove: data.pop(listing, None)
            elif reviewed_observation is not None:
                if listing not in data: raise HTTPException(404, 'Company is not saved')
                data[listing]['reviewed_observation'] = reviewed_observation
            else:
                previous = data.get(listing, {}).get('reviewed_observation')
                data[listing] = entry.model_dump(mode='json')
                data[listing]['reviewed_observation'] = previous
            fd, tmp = tempfile.mkstemp(dir=root)
            try:
                with os.fdopen(fd, 'w') as target:
                    json.dump(data, target); target.flush(); os.fsync(target.fileno())
                os.replace(tmp, path)
                directory = os.open(root, os.O_RDONLY)
                try: os.fsync(directory)
                finally: os.close(directory)
            finally:
                if os.path.exists(tmp): os.unlink(tmp)
        return dict(entries=data)
