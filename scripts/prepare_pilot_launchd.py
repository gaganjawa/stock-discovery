"""Write an INACTIVE user LaunchAgent for the existing worker. Never installs it."""
import argparse
import os
import plistlib
from pathlib import Path


def definition(python,repo,pilot,schedule,database,operations):
    paths=[Path(p).absolute() for p in (python,repo,pilot,schedule,database,operations)]
    python,repo,pilot,schedule,database,operations=map(str,paths)
    for path in paths:
        if not path.exists():raise ValueError('launch_path_missing')
    return {'Label':'local.stock-discovery.research','ProgramArguments':[python,'-m','worker.main','--schedule-config',schedule,'--real-pilot-config',pilot,'--pilot-operations-directory',operations,'--interval-seconds','30'],
        'WorkingDirectory':repo,'EnvironmentVariables':{'PYTHONPATH':':'.join(str(Path(repo)/x) for x in ('backend','shared','worker')),'DATABASE_URL_FILE':database,'PYTHONUNBUFFERED':'1'},
        'RunAtLoad':True,'KeepAlive':True,'ThrottleInterval':60,'ProcessType':'Background','Nice':10,'ExitTimeOut':30,'Umask':63,
        # Worker writes a bounded private diagnostic ring. No unbounded launchd stdout files.
        'StandardOutPath':'/dev/null','StandardErrorPath':'/dev/null'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('python','repo','pilot','schedule','database','operations','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();out=a.output.expanduser().resolve()
    if out.exists() or 'LaunchAgents' in out.parts:raise ValueError('output_must_be_new_inactive_review_file')
    data=definition(a.python,a.repo,a.pilot,a.schedule,a.database,a.operations)
    with open(out,'xb') as f:os.chmod(out,0o600);plistlib.dump(data,f)
    print('Prepared inactive LaunchAgent; explicit owner authorization required before install/bootstrap.')


if __name__=='__main__':main()
