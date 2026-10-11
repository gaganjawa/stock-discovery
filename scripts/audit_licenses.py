"""STK-009: snapshot local locked metadata; no installs, upgrades or network calls.
Run with .venv/bin/python from repo root; running Compose services are required.
Metadata declarations are evidence, not a compliance verdict. See docs/STK-009.md.
"""
import hashlib
import importlib.metadata as md
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/licenses'

def run(*args):
    return subprocess.check_output(args, cwd=ROOT, text=True)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')

def texts(folder):
    return sorted(p for p in folder.rglob('*') if p.is_file()
                  and re.match(r'^(licen[sc]e|copying|notice)([.-]|$)', p.name, re.I)
                  and 'node_modules' not in p.relative_to(folder).parts)

def main():
    OUT.mkdir(exist_ok=True)
    lock=json.loads((ROOT/'frontend/package-lock.json').read_text())['packages']
    direct={**lock[''].get('dependencies',{}),**lock[''].get('devDependencies',{})}
    npm=[]; notice=['Stock Discovery third-party notices — STK-009\n\nIncludes browser runtime and installed build/test dependencies.\nUnmodified upstream texts follow; see docs/STK-009.md for scope and gaps.\n\nTradingView Lightweight Charts™\nCopyright (с) 2025 TradingView, Inc. https://www.tradingview.com/\nInstalled distribution also retains: Copyright (c) 2026 TradingView, Inc.\n']
    for key,v in sorted(lock.items()):
        if not key: continue
        folder=ROOT/'frontend'/key; name=key.split('node_modules/')[-1]
        installed=(folder/'package.json').exists(); files=texts(folder) if installed else []
        meta=json.loads((folder/'package.json').read_text()) if installed else {}
        assert not installed or meta['version']==v['version'],name
        npm.append(dict(package=name,version=v['version'],direct=name in direct,license=v.get('license','UNKNOWN'),source=v.get('resolved'),integrity=v.get('integrity'),installed=installed,repository=meta.get('repository'),evidence=key+'/package.json' if installed else 'frontend/package-lock.json',notice_files=[str(p.relative_to(ROOT)) for p in files],issue='No installed licence text' if not files else None))
        for p in files:
            notice.append(f'\n===== {name} {v["version"]}: {p.relative_to(folder)} =====\n'+p.read_text(errors='replace'))
    extras=OUT/'upstream'
    if extras.exists():
        for p in sorted(extras.glob('*.txt')):
            notice.append(f'\n===== Supplement: {p.name} =====\n'+p.read_text())
    (ROOT/'frontend/public/THIRD-PARTY-NOTICES.txt').write_text('\n'.join(notice))
    save('frontend.json',npm)
    # Collect platform-specific metadata from both local macOS and Linux runtime.
    code='''import importlib.metadata as m,json
result={}
for d in m.distributions():
 files=[f for f in d.files or [] if any(x in str(f).lower() for x in ('license','copying','notice')) and not str(f).endswith(('.py','.pyc'))]
 result[d.metadata['Name'].lower().replace('_','-')]={'version':d.version,'license':d.metadata.get('License-Expression') or d.metadata.get('License') or 'UNKNOWN','classifiers':[v for v in d.metadata.get_all('Classifier',[]) if 'License ::' in v],'source':d.metadata.get_all('Project-URL',[]) or [d.metadata.get('Home-page')],'notices':{str(f):d.locate_file(f).read_text(errors='replace') for f in files if d.locate_file(f).is_file()},'bundled_libraries':[str(f) for f in d.files or [] if '.libs/' in str(f)]}
print(json.dumps(result))'''
    local=json.loads(run(str(ROOT/'.venv/bin/python'),'-c',code))
    linux=json.loads(run('docker-compose','exec','-T','api','python','-c',code))
    worker=json.loads(run('docker-compose','exec','-T','worker','python','-c',code))
    assert linux==worker,'API/worker installed metadata differs'
    py=[]; pynotices=[]
    roots=set(re.findall(r'^([\w-]+)',(ROOT/'backend/requirements.in').read_text(),re.M))
    for name,version in re.findall(r'^([\w-]+)==([^\s]+)',(ROOT/'backend/requirements.txt').read_text(),re.M):
        evidence=linux.get(name) or local.get(name)
        row=dict(package=name,version=version,direct=name in roots,source=f'https://pypi.org/project/{name}/{version}/',installed_linux=name in linux,installed_local=name in local)
        if evidence:
            assert evidence['version']==version
            row.update({k:v for k,v in evidence.items() if k!='notices'})
            row['notice_files']=list(evidence['notices'])
            for platform,data in [('Linux',linux.get(name)),('macOS',local.get(name))]:
                if data:
                    for file,content in data['notices'].items():pynotices.append(f'\n===== {name} {version} ({platform}): {file} =====\n'+content)
        else: row.update(license='UNKNOWN',issue='Not installed on inspected Linux/macOS; conditional lock entry; review before enabling platform')
        py.append(row)
    save('python.json',py)
    (OUT/'python-NOTICES.txt').write_text('\n'.join(pynotices))
    containers=[]
    node=re.search(r'FROM (\S+)',(ROOT/'frontend/Dockerfile').read_text())[1]
    for scope,command in [('api',['docker-compose','exec','-T','api']),('database',['docker-compose','exec','-T','database']),('web',['docker-compose','exec','-T','web']),('node-build',['docker','run','--rm','--network','none','--entrypoint','sh',node])]:
        if scope=='api':
            code2="""import subprocess,pathlib,re,json
rows=[]
for line in subprocess.check_output(['dpkg-query','-W','-f','${Package}\\t${Version}\\n'],text=True).splitlines():
 name,version=line.split('\\t');p=pathlib.Path('/usr/share/doc')/name/'copyright';t=p.read_text(errors='replace') if p.exists() else ''
 rows.append(dict(package=name,version=version,license=sorted(set(re.findall(r'^License: (.+)',t,re.M))) or ['UNRESOLVED: see copyright text'],source=re.findall(r'^(?:Source|Upstream-Source): (.+)',t,re.M),evidence=str(p),copyright_text=t))
print(json.dumps(rows))"""
            packages=json.loads(run(*command,'python','-c',code2))
        else:
            raw=run(*command,*(['-c'] if scope=='node-build' else ['sh','-c']),'cat /lib/apk/db/installed')
            packages=[]
            for block in raw.split('\n\n'):
                d=dict(line.split(':',1) for line in block.splitlines() if len(line)>1 and line[1]==':')
                if 'P' in d: packages.append(dict(package=d['P'],version=d['V'],license=d.get('L') or 'UNRESOLVED/virtual',source=d.get('U'),origin=d.get('o'),source_commit=d.get('c'),evidence='/lib/apk/db/installed'))
        containers.append(dict(scope=scope,packages=packages))
    save('containers.json',containers)
    save('inputs.json',{p:digest(ROOT/p) for p in ['frontend/package-lock.json','backend/requirements.txt','frontend/Dockerfile','backend/Dockerfile','worker/Dockerfile','compose.yaml']})
    print(f'Inventory: {len(npm)} npm lock entries, {len(py)} Python pins, '+str(sum(len(c['packages']) for c in containers))+' OS package records')
    print('Installed npm without notice:',[r['package'] for r in npm if r['installed'] and r['issue']])

if __name__=='__main__':main()
