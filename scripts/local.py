"""Local-only launcher. Preserves existing settings and never prints secrets."""
import argparse
import os
from pathlib import Path
import secrets
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def prepare(root):
    path=root/'.env'
    text=path.read_text() if path.exists() else (root/'.env.example').read_text()
    lines=text.splitlines()
    values={line.split('=',1)[0].strip():line.split('=',1)[1].strip().strip('\"\'')
            for line in lines if '=' in line and not line.lstrip().startswith('#')}
    if not values.get('AUTH_TOKEN'):
        lines=[line for line in lines if not line.startswith('AUTH_TOKEN=')]
        lines.append('AUTH_TOKEN='+secrets.token_urlsafe(32))
    path.write_text('\n'.join(lines)+'\n')
    path.chmod(0o600)
    return values


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('start','stop','status'),default='start',nargs='?')
    args=parser.parse_args()
    values=prepare(ROOT)
    docker=shutil.which('docker')
    if docker and subprocess.run([docker,'compose','version'],capture_output=True).returncode==0:
        compose=[docker,'compose']
    elif shutil.which('docker-compose'): compose=[shutil.which('docker-compose')]
    else: raise SystemExit('Install/start Docker with Compose, then retry. Your .env is ready.')
    env=os.environ.copy()
    port=env.get('WEB_PORT',values.get('WEB_PORT','5173'))
    if not port.isdigit() or not 1<=int(port)<=65535: raise SystemExit('WEB_PORT must be a valid port number.')
    env.update(COOKIE_SECURE='false',APP_ORIGIN='http://127.0.0.1:'+port)
    if env.get('CODE_VERSION',values.get('CODE_VERSION','local-unversioned'))=='local-unversioned':
        rev=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True)
        if rev.returncode==0: env['CODE_VERSION']=rev.stdout.strip()
    command={'start':['up','--build','-d'],'stop':['stop'],'status':['ps']}[args.action]
    subprocess.run(compose+command,cwd=ROOT,env=env,check=True)
    if args.action=='start':
        print('Open http://127.0.0.1:'+port)
        print('Sign in with AUTH_TOKEN from '+str(ROOT/'.env')+'. Load synthetic history from Dashboard.')


if __name__=='__main__': main()
