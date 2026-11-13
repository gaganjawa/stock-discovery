"""STK-099 isolated full Compose rehearsal. Synthetic only; never a production host.

Requires locally built stk099-{api,worker,web}:acceptance images. Creates a uniquely
named Compose project with loopback HTTPS and its own volumes. Leaves stopped
artifacts for inspection; never removes volumes. No real configuration is loaded.
"""
import argparse
import base64
import json
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import sys
import time
import urllib.request
import urllib.error
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'shared'),str(ROOT/'backend'),str(ROOT/'worker')]
from stock_discovery_analysis.real_views import ViewConfig
from stock_discovery_analysis.chartink import Scanner
from stk099_transfer import Database, backup, restore


def run(directory,context):
    directory.mkdir(mode=0o700,parents=True,exist_ok=False)
    directory=directory.resolve()
    for child in ['secrets','private','watchlist','config']:(directory/child).mkdir(mode=0o700)
    secrets=directory/'secrets'
    password='synthetic-stk099-no-production-password-012345'
    files=dict(db_password=password,owner_url=f'postgresql://chartink_owner:{password}@database/chartink_inbox',
               receiver_url=f'postgresql://chartink_receiver:{password}@database/chartink_inbox',
               app_url=f'postgresql://stk_runtime:{password}@database/stk_real001_private',
               worker_url=f'postgresql://stk_candidate_worker:{password}@database/stk_real001_private',
               source_url=f'postgresql://stk_inbox_reader:{password}@database/chartink_inbox',
               app_owner_url=f'postgresql://stk_app_owner:{password}@database/stk_real001_private',
               webhook='w'*40,pull='p'*40,owner_access='o'*40)
    for name,value in files.items():(secrets/name).write_text(value)
    scanner=Scanner(scan_name='Synthetic EOD',scan_url='synthetic-eod',alert_name='Synthetic',version='1',
                    rules='Isolated STK-099 fixture only',rights_reference='SYNTHETIC',enabled_until='2028-01-01T00:00:00Z',mode='provider_alert')
    (secrets/'scanner.json').write_text(scanner.model_dump_json())
    # Minimal stored-only view: no grants, policy or provider credentials.
    view=ViewConfig(sources=dict(grant_file='/run/private/grants.json',retention_days=30),listing_ids=('NSE:SYN097',))
    (directory/'private/view.json').write_text(view.model_dump_json())
    (directory/'private/grants.json').write_text('[]')
    docker=['docker']+(['--context',context] if context else [])
    hashed=subprocess.check_output(docker+['run','--rm','caddy:2.10.2-alpine','caddy','hash-password','--plaintext',password],text=True).strip()
    (secrets/'ui_auth').write_text('owner '+hashed+'\n')
    for p in secrets.iterdir():p.chmod(0o644) # synthetic only; parent stays private
    # Container UID owns its synthetic metadata path; no production path is used.
    subprocess.run(docker+['run','--rm','--user','0:0','-v',str(directory/'watchlist')+':/data','--entrypoint','sh','stk099-api:acceptance','-c','chown 10001:10001 /data && chmod 700 /data'],check=True)
    subprocess.run(docker+['run','--rm','--user','0:0','-v',str(directory/'private')+':/data','--entrypoint','sh','stk099-api:acceptance','-c','chown -R 10001:10001 /data && chmod 700 /data && chmod 600 /data/*'],check=True)
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    host='https://localhost:'+str(port)
    caddy=(ROOT/'deploy/bookmyhost/Caddyfile').read_text().replace('{$RECEIVER_DOMAIN} {','localhost {\n    tls internal')
    (directory/'config/Caddyfile').write_text(caddy)
    project='stk099-test-'+uuid4().hex[:8]
    override=directory/'override.yaml'
    override.write_text('services:\n  proxy:\n    ports: !override ["127.0.0.1:'+str(port)+':443"]\n  api:\n    environment:\n      APP_ORIGIN: '+host+'\n  worker:\n    environment:\n      APP_ORIGIN: '+host+'\n')
    env={**os.environ,'CHARTINK_SECRETS_DIR':str(secrets),'STK099_SECRETS_DIR':str(secrets),
         'STK099_CONFIG_DIR':str(directory/'config'),'STK099_PRIVATE_DIR':str(directory/'private'),
         'STK099_WATCHLIST_DIR':str(directory/'watchlist'),'RECEIVER_DOMAIN':'localhost',
         'CHARTINK_RECEIVER_URL':'https://synthetic.invalid','CHARTINK_RECEIVER_ENABLED':'true',
         'API_IMAGE':'stk099-api:acceptance','WORKER_IMAGE':'stk099-worker:acceptance',
         'WEB_IMAGE':'stk099-web:acceptance','CODE_VERSION':'STK-099-isolated-acceptance'}
    if context:env['DOCKER_CONTEXT']=context
    compose_base=['docker-compose'] if shutil.which('docker-compose') else docker+['compose']
    compose=compose_base+['-p',project,'-f',str(ROOT/'deploy/chartink/compose.yaml'),
                    '-f',str(ROOT/'deploy/bookmyhost/compose.yaml'),'-f',str(override),'--profile','receiver']
    def dc(*args,**kwargs):
        completed=subprocess.run(compose+list(args),env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,**kwargs)
        if completed.returncode:
            (directory/'compose-failure.log').write_bytes(completed.stdout+completed.stderr)
            raise RuntimeError('isolated_compose_failed_see_private_log')
        return completed.stdout
    (directory/'project.json').write_text(json.dumps(dict(project=project,port=port)))
    dc('config','--quiet')
    dc('up','-d','--wait','database')
    container=dc('ps','-q','database').decode().strip()
    db=Database(container,'chartink_owner','chartink_inbox',context)
    try:
        dc('run','--rm','--no-deps','migrate')
        for role in ['chartink_receiver','stk_app_owner','stk_runtime','stk_candidate_worker','stk_inbox_reader']:
            db.sql(f"CREATE ROLE {role} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD '{password}'")
        db.sql('CREATE DATABASE stk_real001_private OWNER stk_app_owner')
        dc('run','--rm','--no-deps','-v',str(secrets/'app_owner_url')+':/tmp/app_owner_url:ro','-e','DATABASE_URL_FILE=/tmp/app_owner_url','migrate')
        for name,database in [('deploy/chartink/grants.sql','chartink_inbox'),('deploy/bookmyhost/source-grants.sql','chartink_inbox'),('deploy/bookmyhost/grants.sql','stk_real001_private')]:
            db.sql((ROOT/name).read_text(),database)
        started=time.monotonic();dc('up','-d','--no-build','--wait','receiver','api','worker','web','proxy')
        startup_seconds=time.monotonic()-started
        tls=ssl._create_unverified_context() # Only generated localhost TLS.
        basic='Basic '+base64.b64encode(('owner:'+password).encode()).decode()
        def request(path,body=None,headers=None):
            data=json.dumps(body).encode() if body is not None else None
            req=urllib.request.Request(host+path,data=data,headers=headers or {})
            try:
                with urllib.request.urlopen(req,context=tls,timeout=10) as response:return response.status,response.read()
            except urllib.error.HTTPError as exc:return exc.code,exc.read()
        assert request('/')[0]==401
        assert request('/healthz')[0]==404
        assert request('/docs')[0]==404
        assert request('/',headers={'Authorization':basic})[0]==200
        assert request('/v1/real-research/candidates',headers={'Authorization':basic})[0]==401
        assert request('/hooks/chartink/wrong',{}, {'Content-Type':'application/json'})[0]==401
        dc('stop','worker')
        payload=dict(stocks='SYN097',trigger_prices='100',triggered_at='6:00 pm',scan_name=scanner.scan_name,scan_url=scanner.scan_url,alert_name=scanner.alert_name)
        status,_=request('/hooks/chartink/'+'w'*40,payload,{'Content-Type':'application/json'});assert status==202
        assert db.sql('SELECT count(*) FROM discovery.candidate_events')=='1'
        # New provider-test format must never materialize candidates/research.
        probe_payload=json.loads((ROOT/'backend/tests/fixtures/chartink_provider_test_v1.json').read_text())
        probe_payload.update({k:getattr(scanner,k) for k in ('scan_name','scan_url','alert_name')})
        status,receipt=request('/hooks/chartink/'+'w'*40,probe_payload,{'Content-Type':'application/json'})
        assert status==202 and json.loads(receipt)['delivery_kind']=='provider_test'
        assert json.loads(request('/hooks/chartink/'+'w'*40,probe_payload,{'Content-Type':'application/json'})[1])['duplicate']
        dc('up','-d','--no-deps','worker')
        appdb=Database(container,'chartink_owner','stk_real001_private',context)
        def wait_rows(n):
            for _ in range(100):
                if appdb.sql("SELECT count(*) FROM discovery.candidates WHERE research_status='blocked'")==str(n):return
                time.sleep(.3)
            raise AssertionError('worker_timeout')
        wait_rows(1)
        assert appdb.sql('SELECT version_num FROM alembic_version')=='0017'
        assert db.sql('SELECT version_num FROM alembic_version')=='0017'
        assert json.loads(request('/hooks/chartink/'+'w'*40,payload,{'Content-Type':'application/json'})[1])['duplicate']
        if os.getenv('STK099_STACK_BROWSER')=='1':
            subprocess.run(['node',str(ROOT/'scripts/stk099_hosted_browser.cjs')],check=True,timeout=90,
                env={**os.environ,'STK_URL':host,'STK_EDGE_PASSWORD':password,
                     'STK_PLAYWRIGHT':str(ROOT/'frontend/node_modules/@playwright/test')})
        ids=dc('ps','-q').decode().split()
        samples=[]
        for index,count in enumerate((35,40,50,150)):
            symbols=[f'SYN{index:02d}{j:03d}' for j in range(count)]
            row={k:100 for k in probe_payload['columns'][0]}
            row.update(sector='Synthetic',industry='Invented',marketcapname='Test',rsi14=60)
            data={**payload,'stocks':','.join(symbols),'trigger_prices':','.join(['100']*count),
                  'columns':[{**row,'symbol':symbol} for symbol in symbols]}
            assert len(json.dumps(data).encode())<65536
            assert request('/hooks/chartink/'+'w'*40,data,{'Content-Type':'application/json'})[0]==202
            samples.append(subprocess.check_output(docker+['stats','--no-stream','--format','{{json .}}',*ids],text=True))
        wait_rows(276)
        assert appdb.sql("SELECT count(*) FROM discovery.candidate_research_runs WHERE result->'reasons' = '[\"nse_identity_missing_or_ambiguous\"]'::jsonb")=='276'
        cursor_before=appdb.sql('SELECT receiver_id,cursor FROM discovery.candidate_receivers ORDER BY 1')
        dc('restart','worker');wait_rows(276)
        assert appdb.sql('SELECT receiver_id,cursor FROM discovery.candidate_receivers ORDER BY 1')==cursor_before
        assert appdb.sql("SELECT count(*) FROM discovery.candidate_events WHERE envelope->>'version'='chartink-provider-test-v1'")=='1'
        assert appdb.sql('SELECT count(*) FROM discovery.candidate_matches')=='276'
        assert appdb.sql('SELECT count(*) FROM discovery.candidate_research_runs')=='276'
        inspect=json.loads(subprocess.check_output(docker+['inspect',*ids]))
        for item in inspect:
            assert not item['State']['OOMKilled']
            if item['Config']['Labels']['com.docker.compose.service']!='proxy':
                assert not any(item['NetworkSettings']['Ports'].values())
        # No egress from worker/API: only internal Compose network attachments.
        for item in inspect:
            if item['Config']['Labels']['com.docker.compose.service'] in ('worker','api','database','web','receiver'):
                for network in item['NetworkSettings']['Networks']:
                    assert json.loads(subprocess.check_output(docker+['network','inspect',network]))[0]['Internal']
        dc('stop','worker')
        probe=json.loads(dc('run','--rm','--no-deps',
            '-v',str(secrets/'owner_url')+':/tmp/probe_owner_url:ro',
            '-v',str(ROOT/'backend/tests/integration')+':/probe/tests:ro',
            '-v',str(ROOT/'worker/worker')+':/probe/worker:ro',
            '-v',str(ROOT/'scripts/stk099_research_probe.py')+':/probe/run.py:ro',
            '-e','DATABASE_URL_FILE=/tmp/probe_owner_url',
            '-e','PYTHONPATH=/app:/app/shared:/probe:/probe/tests',
            'api','python','/probe/run.py'))
        assert probe['stored_research_bars']==30 and probe['permission_denial_verified']
        dump=directory/'synthetic.dump';manifest=backup(appdb,dump,db.sql('SELECT system_identifier FROM pg_control_system()'))
        restored=Database(container,'chartink_owner','stk099_restore_check',context)
        restore(restored,dump,manifest,'stk_app_owner')
        assert db.sql('SELECT count(*) FROM discovery.candidate_events')=='6'
        result=dict(synthetic_only=True,project=project,startup_seconds=round(startup_seconds,2),
                    research_probe=probe,research_path='stored_identity_lookup_no_evidence',candidates=276,events=6,provider_test_isolated=True,large_batches=[35,40,50,150],duplicate_deduplicated=True,worker_restart=True,
                    authenticated_https=True,network_isolation=True,restore_all_tables_and_sequences=True,
                    browser_verified=os.getenv('STK099_STACK_BROWSER')=='1',
                    resource_samples=[json.loads(line) for sample in samples for line in sample.splitlines()],
                    architecture=subprocess.check_output(docker+['info','--format','{{.Architecture}}'],text=True).strip())
        (directory/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:v for k,v in result.items() if k!='resource_samples'},indent=2))
    finally:
        # Preserve all disposable volumes and logs; stop only this unique project.
        dc('stop')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    parser.add_argument('--context',default='colima')
    args=parser.parse_args()
    run(args.directory,args.context)
