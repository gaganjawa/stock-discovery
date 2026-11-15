"""STK-099 isolated restored-data rehearsal; never updates the live Compose project.

Input: app.dump/manifest, inbox.dump/manifest, bundle/, scanner.json and prior-url.
All provider credentials are deliberately absent. Real data is read only through
private APIs; no synthetic candidate is inserted into either production database.
"""
import argparse,base64,json,os,secrets,shutil,socket,ssl,subprocess,time,urllib.request,urllib.error
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4
from stk099_transfer import Database,restore,backup,checksum

ROOT=Path(__file__).resolve().parents[1]
MIB=1024**2

def run(directory, app_cluster, inbox_cluster):
    os.umask(0o077);directory=directory.resolve()
    assert directory.is_dir() and not (directory/'project.json').exists(),'new_rehearsal_directory_required'
    for name in ('app','inbox'):
        assert checksum(directory/(name+'.dump'))==json.loads((directory/(name+'.manifest.json')).read_text())['sha256']
    hashes=json.loads((directory/'bundle/files.sha256.json').read_text())
    for name,value in hashes.items():assert checksum(directory/'bundle'/name)==value,'bundle_changed'
    subprocess.run(['docker','run','--rm','--network','none','--entrypoint','python',os.environ['WORKER_IMAGE'],'-c','import worker.candidate_prices; import stock_discovery_analysis.runtime'],check=True)
    project='stk099-rep-'+uuid4().hex[:8]
    private=directory/'bundle/private';watchlist=directory/'bundle/watchlist'
    secret=directory/'secrets';secret.mkdir(mode=0o700)
    refresh=directory/'refresh';refresh.mkdir(mode=0o700)
    config=directory/'config';config.mkdir(mode=0o700)
    password=secrets.token_hex(32)
    values=dict(db_password=password,owner_url=f'postgresql://chartink_owner:{password}@database/chartink_inbox',
        receiver_url=f'postgresql://chartink_receiver:{password}@database/chartink_inbox',
        app_url=f'postgresql://stk_runtime:{password}@database/stk_real001_private',
        worker_url=f'postgresql://stk_candidate_worker:{password}@database/stk_real001_private',
        source_url=f'postgresql://stk_inbox_reader:{password}@database/chartink_inbox',
        refresh_url=f'postgresql://stk_price_refresh:{password}@database/stk_real001_private',
        webhook=secrets.token_hex(32),pull=secrets.token_hex(32),owner_access=secrets.token_hex(32),
        upstox_token='REHEARSAL_NO_PROVIDER_CREDENTIAL')
    for name,value in values.items():(secret/name).write_text(value)
    shutil.copyfile(directory/'scanner.json',secret/'scanner.json')
    hashed=subprocess.check_output(['docker','run','--rm','--network','none','caddy:2.10.2-alpine','caddy','hash-password','--plaintext',password],text=True).strip()
    (secret/'ui_auth').write_text('owner '+hashed+'\n')
    # UID 10001 can read only this private rehearsal tree; no live files mounted.
    for p in [private,watchlist,refresh]:
        os.chown(p,10001,10001)
        for f in p.iterdir():os.chown(f,10001,10001);f.chmod(0o600)
    for p in secret.iterdir():os.chown(p,10001,10001);p.chmod(0o400)
    (secret/'db_password').chmod(0o444)  # Isolated generated credential, PostgreSQL UID 999.
    # No candidate admission or provider calls: restored zero-candidate baseline.
    (refresh/'grants.json').write_text('[]');os.chown(refresh/'grants.json',10001,10001)
    (refresh/'refresh.json').write_text(json.dumps(dict(market=dict(account_ref='stk099-isolated-no-acquisition',grant_file='/run/refresh/grants.json',token_file='/run/secrets/upstox_token',symbols=['INFY'],lookback_days=44,retention_days=30),scanner_keys=['rehearsal-disabled'],candidate_days=3,max_symbols=1)))
    os.chown(refresh/'refresh.json',10001,10001)
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    host='https://localhost:'+str(port)
    (config/'Caddyfile').write_text((ROOT/'deploy/bookmyhost/Caddyfile').read_text().replace('{$RECEIVER_DOMAIN} {','localhost {\n tls internal'))
    override=directory/'override.yaml'
    override.write_text('services:\n  proxy:\n    ports: !override ["127.0.0.1:'+str(port)+':443"]\n  api:\n    environment:\n      APP_ORIGIN: '+host+'\n  worker:\n    environment:\n      APP_ORIGIN: '+host+'\n  price-refresh:\n    networks: !override [private]\n')
    env={**os.environ,'CHARTINK_SECRETS_DIR':str(secret),'STK099_SECRETS_DIR':str(secret),'STK099_CONFIG_DIR':str(config),
        'STK099_PRIVATE_DIR':str(private),'STK099_WATCHLIST_DIR':str(watchlist),'STK099_REFRESH_DIR':str(refresh),
        'RECEIVER_DOMAIN':'localhost','CHARTINK_RECEIVER_URL':(directory/'prior-url').read_text().strip(),
        'CHARTINK_RECEIVER_ENABLED':'false','CODE_VERSION':os.environ['CODE_VERSION'],
        'API_IMAGE':os.environ['API_IMAGE'],'WORKER_IMAGE':os.environ['WORKER_IMAGE'],'WEB_IMAGE':os.environ['WEB_IMAGE']}
    compose=['docker','compose','-p',project,'-f',str(ROOT/'deploy/chartink/compose.yaml'),'-f',str(ROOT/'deploy/bookmyhost/compose.yaml'),'-f',str(ROOT/'deploy/bookmyhost/compose.refresh.yaml'),'-f',str(override),'--profile','receiver','--profile','price-refresh']
    def dc(*args):
        r=subprocess.run(compose+list(args),env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        if r.returncode:
            (directory/'failure.private.log').write_bytes(r.stdout+r.stderr)
            raise RuntimeError('rehearsal_compose_failure')
        return r.stdout.decode().strip()
    (directory/'project.json').write_text(json.dumps(dict(project=project,port=port)))
    baseline=json.loads(subprocess.check_output(['docker','inspect',*subprocess.check_output(['docker','ps','-q'],text=True).split()]))
    live={i['Name']:(i['Id'],i['State']['StartedAt'],i['Image']) for i in baseline}
    samples=[]
    def sample():
        mem={l.split(':')[0]:int(l.split()[1])*1024 for l in Path('/proc/meminfo').read_text().splitlines()}
        record=dict(at=time.time(),available=mem['MemAvailable'],swap_used=mem['SwapTotal']-mem['SwapFree'],containers=[json.loads(l) for l in subprocess.check_output(['docker','stats','--no-stream','--format','{{json .}}'],text=True).splitlines()])
        samples.append(record)
        assert record['available']>=384*MIB,'host_headroom_below_384_MiB'
        assert record['swap_used']<256*MIB,'host_swap_pressure'
    started=time.monotonic()
    try:
        sample();dc('config','--quiet');dc('up','-d','--no-build','--wait','database')
        container=dc('ps','-q','database');db=Database(container,'chartink_owner','postgres')
        assert db.sql('SELECT system_identifier FROM pg_control_system()') not in (app_cluster,inbox_cluster),'source_cluster_must_not_be_rehearsal_target'
        for role in ('stock_discovery','stk_restriction_operator','stk_app_owner','chartink_receiver','stk_runtime','stk_candidate_worker','stk_inbox_reader','stk_price_refresh'):
            db.sql(f"CREATE ROLE {role} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD '{password}'")
        # Leave the empty default database intact; restore into a distinct name.
        assert db.sql("SELECT count(*) FROM pg_tables WHERE schemaname='discovery'",'chartink_inbox')=='0'
        # Restore inbox under a new name; no DROP, clean or live destination.
        inbox=Database(container,'chartink_owner','stk099_inbox_restored')
        app=Database(container,'chartink_owner','stk_real001_private')
        for obj,name,owner,cluster in [(inbox,'inbox','chartink_owner',inbox_cluster),(app,'app','stk_app_owner',app_cluster)]:
            restore(obj,directory/(name+'.dump'),json.loads((directory/(name+'.manifest.json')).read_text()),owner,expected_source='chartink_inbox' if name=='inbox' else 'stk_real001_private',expected_source_cluster=cluster)
        # Hosted identity fences require canonical names. Both renames are in
        # the freshly created cluster, after a verified restore to a new target.
        db.sql('ALTER DATABASE chartink_inbox RENAME TO stk099_empty_bootstrap')
        db.sql('ALTER DATABASE stk099_inbox_restored RENAME TO chartink_inbox')
        inbox=Database(container,'chartink_owner','chartink_inbox')
        for path,target in [('deploy/chartink/grants.sql',inbox),('deploy/bookmyhost/source-grants.sql',inbox),('deploy/bookmyhost/grants.sql',app),('deploy/bookmyhost/refresh-grants.sql',app)]:
            target.sql((ROOT/path).read_text())
        original=app.snapshot();inbox_original=inbox.snapshot()
        assert original['revision']==inbox_original['revision']=='0017'
        assert app.sql('SELECT count(*) FROM discovery.candidates')=='0','representative_zero_candidate_baseline_required'
        dc('up','-d','--no-build','--wait','receiver','api','worker','web','proxy','price-refresh');sample()
        tls=ssl._create_unverified_context()
        basic='Basic '+base64.b64encode(('owner:'+password).encode()).decode()
        def request(path):
            req=urllib.request.Request(host+path,headers={'Authorization':basic,'X-Stock-Discovery-Token':values['owner_access']})
            try:
                with urllib.request.urlopen(req,context=tls,timeout=30) as r:return r.status,r.read()
            except urllib.error.HTTPError as e:return e.code,e.read()
        # Establish real application cookie; Basic remains an independent edge gate.
        req=urllib.request.Request(host+'/api/v1/session',data=json.dumps({'token':values['owner_access']}).encode(),headers={'Authorization':basic,'Content-Type':'application/json','Origin':host})
        with urllib.request.urlopen(req,context=tls,timeout=30) as r:cookie=r.headers.get('Set-Cookie','').split(';',1)[0]
        def authenticated(path):
            req=urllib.request.Request(host+path,headers={'Authorization':basic,'Cookie':cookie})
            with urllib.request.urlopen(req,context=tls,timeout=30) as r:return json.loads(r.read())
        watch=authenticated('/v1/real-research/watchlist')
        candidates=authenticated('/v1/real-research/candidates/swing-review?limit=20')
        assert candidates['total']==0
        if os.getenv('STK099_REQUIRE_BROWSER')=='1':
            (directory/'browser-ready.json').write_text(json.dumps(dict(port=port)))
            deadline=time.monotonic()+180
            while not (directory/'browser.ok').exists():
                assert time.monotonic()<deadline,'browser_acceptance_timeout'
                time.sleep(1)
        paths=['/v1/real-research/companies/NSE%3AINE009A01021']*24
        with ThreadPoolExecutor(max_workers=4) as pool:details=list(pool.map(authenticated,paths))
        sample()
        dc('restart','worker','price-refresh');time.sleep(4);sample()
        assert app.snapshot()==original and inbox.snapshot()==inbox_original,'restored_state_changed'
        for name,value in hashes.items():
            if name.startswith('watchlist/'):assert checksum(directory/'bundle'/name)==value,'watchlist_changed'
        recovery=directory/'recovery.dump';manifest=backup(app,recovery,db.sql('SELECT system_identifier FROM pg_control_system()'))
        restore(Database(container,'chartink_owner','stk099_recovery_check'),recovery,manifest,'stk_app_owner',expected_source=app.name,expected_source_cluster=db.sql('SELECT system_identifier FROM pg_control_system()'))
        ids=dc('ps','-q').split();ins=json.loads(subprocess.check_output(['docker','inspect',*ids]))
        assert not any(i['State']['OOMKilled'] for i in ins)
        for i in ins:
            service=i['Config']['Labels']['com.docker.compose.service']
            if service!='proxy':assert not any(i['NetworkSettings']['Ports'].values())
            if service in ('api','worker','price-refresh'):
                for network in i['NetworkSettings']['Networks']:assert json.loads(subprocess.check_output(['docker','network','inspect',network]))[0]['Internal']
        result=dict(project=project,architecture=os.uname().machine,schema='0017',restored_app_tables=len(original['tables']),restored_rows=sum(t['rows'] for t in original['tables'].values()),restored_sequences=len(original['sequences']),fingerprints_preserved=True,watchlist_preserved=True,recovery_restore=True,authenticated_api=True,browser_verified=(directory/'browser.ok').exists(),concurrent_company_reads=len(details),refresh_idle_no_credentials=True,provider_requests=0,genuine_candidate_acceptance=False,elapsed_seconds=round(time.monotonic()-started,2),resources=samples)
        (directory/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='resources'},indent=2))
    finally:
        dc('stop')
        actual=json.loads(subprocess.check_output(['docker','inspect',*map(lambda i:i['Id'],baseline)]))
        assert {i['Name']:(i['Id'],i['State']['StartedAt'],i['Image']) for i in actual}==live,'live_services_changed'
        assert all(i['State']['Running'] and not i['State']['OOMKilled'] for i in actual),'live_service_unhealthy'
        (directory/'resources.json').write_text(json.dumps(samples,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);p.add_argument('--app-source-cluster',required=True);p.add_argument('--inbox-source-cluster',required=True)
    a=p.parse_args();run(a.directory,a.app_source_cluster,a.inbox_source_cluster)
