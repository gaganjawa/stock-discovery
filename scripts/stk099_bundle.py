"""STK-099 copy private view dependencies/watchlist; preserve bytes, remap paths.

No provider/API credentials are copied. Source files remain unchanged. Quiesce
watchlist writes before running; verify again at final cutover. Output is private.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'shared'))
from stock_discovery_analysis.real_views import ViewConfig


def bundle(view_file, watchlist, destination, *, allow_empty_watchlist=False):
    os.umask(0o077)
    source=ViewConfig.model_validate_json(view_file.read_text())
    path=watchlist/'watchlist.json'
    if not watchlist.is_dir():raise ValueError('watchlist_directory_required')
    if path.exists():
        data=path.read_bytes();json.loads(data)
    elif allow_empty_watchlist:
        data=None
    else:raise ValueError('watchlist_file_required')
    destination.mkdir(mode=0o700,parents=False,exist_ok=False)
    config=destination/'private';config.mkdir(mode=0o700)
    saved=destination/'watchlist';saved.mkdir(mode=0o700)
    hashes={}
    def copy(path,name):
        path=Path(path)
        if not path.is_absolute():
            raise ValueError('source_config_paths_must_be_absolute')
        data=path.read_bytes();target=config/name;target.write_bytes(data)
        hashes['private/'+name]=hashlib.sha256(data).hexdigest()
        return '/run/private/'+name
    values=source.model_dump(mode='json')
    values['sources']['grant_file']=copy(source.sources.grant_file,'grants.json')
    if source.policy_file:values['policy_file']=copy(source.policy_file,'policies.json')
    if source.pilot_health_file:
        # Copy as historical metadata; do not claim the stopped Mac job is healthy.
        values['pilot_health_file']=copy(source.pilot_health_file,'previous-pilot-health.json')
    (config/'view.json').write_text(json.dumps(values,indent=2)+'\n')
    hashes['private/view.json']=hashlib.sha256((config/'view.json').read_bytes()).hexdigest()
    # Original config retained as private provenance, never read by containers.
    (destination/'original-view.json').write_bytes(view_file.read_bytes())
    if data is not None:
        (saved/'watchlist.json').write_bytes(data)
        hashes['watchlist/watchlist.json']=hashlib.sha256(data).hexdigest()
        if path.read_bytes()!=data:raise ValueError('watchlist_changed_during_copy')
    elif path.exists() or not watchlist.is_dir():
        raise ValueError('watchlist_changed_during_copy')
    (destination/'watchlist-export.json').write_text(json.dumps(dict(
        source=str(watchlist.resolve()), intentionally_empty=data is None,
        allow_empty_watchlist=allow_empty_watchlist))+'\n')
    (destination/'files.sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
    print('Copied private configuration and watchlist; original files unchanged.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--view',type=Path,required=True)
    p.add_argument('--watchlist',type=Path,required=True)
    p.add_argument('--destination',type=Path,required=True)
    p.add_argument('--allow-empty-watchlist',action='store_true',help='Audit an intentionally absent watchlist.json in an existing directory')
    a=p.parse_args();bundle(a.view,a.watchlist,a.destination,allow_empty_watchlist=a.allow_empty_watchlist)
