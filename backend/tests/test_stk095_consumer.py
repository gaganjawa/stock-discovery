import importlib.util
import json
import os
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace
import pytest

spec=importlib.util.spec_from_file_location('consumer',Path(__file__).resolve().parents[2]/'scripts/stk095_consumer.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def put(path,value):
    path.write_text(value);path.chmod(0o600);return str(path)


@pytest.fixture
def config(tmp_path):
    repo=tmp_path/'repo';(repo/'worker/worker').mkdir(parents=True)
    (repo/'worker/worker/main.py').write_text('')
    state=tmp_path/'state';state.mkdir(mode=0o700)
    scanner=put(tmp_path/'scanner','{}');secret=put(tmp_path/'secret','s'*40)
    env=put(tmp_path/'env',f'CHARTINK_RECEIVER_URL=https://example.test\nCHARTINK_PULL_SECRET_FILE={secret}\nCHARTINK_SCANNER_CONFIG={scanner}\n')
    return dict(repo=str(repo),python=sys.executable,state_directory=str(state),environment_file=env,
        database_file=put(tmp_path/'db','never-print-secret'),view_file=put(tmp_path/'view','{}'),
        authorization_file=put(tmp_path/'approval',json.dumps(dict(scanner_key='key',rights_reference='approved-test',
          scopes=sorted(m.SCOPES),evidence_reference='isolated test only',enabled_until='2099-01-01T00:00:00+00:00'))),
        database='isolated',receiver_id='identity')


def test_environment_does_not_inherit_provider_or_hosted_settings(config,monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','not-inherited');monkeypatch.setenv('CANDIDATE_SOURCE_DATABASE_URL','not-inherited')
    env=m.environment(config)
    assert 'OPENAI_API_KEY' not in env and 'CANDIDATE_SOURCE_DATABASE_URL' not in env
    assert env['DATABASE_URL_FILE']==config['database_file']


@pytest.mark.parametrize('line',['OPENAI_API_KEY=foo','CHARTINK_RECEIVER_URL=https://duplicate.test','bad'])
def test_rejects_extra_duplicate_and_malformed_env(config,line):
    with open(config['environment_file'],'a') as f:f.write(line+'\n')
    with pytest.raises(ValueError):m.environment(config)


def test_rejects_readable_secret(config):
    Path(config['database_file']).chmod(0o644)
    with pytest.raises(ValueError,match='private_file_required'):m.environment(config)


def test_plist_is_inactive_and_contains_no_secret(config,tmp_path):
    result=m.definition(tmp_path/'manifest.json',config)
    assert result['Label']==m.LABEL
    assert 'never-print-secret' not in str(result)
    assert result['StandardErrorPath']=='/dev/null'


class Connection:
    user='stk_candidate_worker';schema='0017';cursor=(12,);grant=True;privileged=False
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def execute(self,sql,args=None):
        assert not any(x in sql.upper() for x in ['INSERT ','UPDATE ','DELETE ','ALTER '])
        if 'current_database' in sql:self.row=('isolated',self.user)
        elif 'rolsuper' in sql:self.row=(self.privileged,False,False,False)
        elif 'version_num' in sql:self.row=(self.schema,)
        elif 'SELECT cursor' in sql:self.row=self.cursor
        else:self.row=(self.grant,)
        return self
    def fetchone(self):return self.row


@pytest.fixture
def preflight_fixture(config,monkeypatch,tmp_path):
    from stock_discovery_analysis import chartink,candidate_store,real_views
    scanner=SimpleNamespace(mode='provider_alert',enabled_until=m.datetime(2099,1,1,tzinfo=m.timezone.utc),key='key',rights_reference='approved-test')
    monkeypatch.setattr(chartink.Scanner,'model_validate_json',lambda *_:scanner)
    monkeypatch.setattr(candidate_store,'digest',lambda *_:'identity')
    grants=put(tmp_path/'grants','[]')
    monkeypatch.setattr(real_views.ViewConfig,'model_validate_json',lambda *_:SimpleNamespace(sources=SimpleNamespace(grant_file=grants),policy_file=None))
    return scanner,Connection()


def test_preflight_preserves_existing_cursor(config,preflight_fixture):
    _,conn=preflight_fixture
    _,cursor=m.preflight(config,connect=lambda *a,**k:conn)
    assert cursor==12


@pytest.mark.parametrize('field,value,error',[
    ('user','stock_discovery','database_identity_mismatch'),('schema','0016','schema_0017_required'),
    ('cursor',None,'existing_cursor_required'),('grant',False,'required_grant_missing'),
    ('privileged',True,'restricted_role_required')])
def test_preflight_fails_closed(config,preflight_fixture,field,value,error):
    _,conn=preflight_fixture;setattr(conn,field,value)
    with pytest.raises(ValueError,match=error):m.preflight(config,connect=lambda *a,**k:conn)


def test_pending_rights_never_connects(config,preflight_fixture):
    scanner,_=preflight_fixture;scanner.rights_reference='review-pending'
    approval=json.loads(Path(config['authorization_file']).read_text());approval['rights_reference']='review-pending'
    put(Path(config['authorization_file']),json.dumps(approval))
    with pytest.raises(ValueError,match='scanner_rights_review_pending'):
        m.preflight(config,connect=lambda *a,**k:pytest.fail('must not connect'))


def test_restart_and_singleton(config,tmp_path):
    # Real child processes, no network/production database. Database replay is
    # independently exercised by existing PostgreSQL candidate recovery tests.
    package=Path(config['repo'])/'worker/worker'
    (package/'__init__.py').write_text('')
    count=tmp_path/'cycles'
    (package/'main.py').write_text('from pathlib import Path\nimport time\np=Path('+repr(str(count))+')\np.write_text(str(int(p.read_text())+1) if p.exists() else "1")\ntime.sleep(30)\n')
    env=m.environment(config)
    check=lambda _: (env,12)
    for expected in (1,2):
        stop=threading.Event();errors=[]
        def run():
            try:m.supervise(config,check=check,stop=stop,interval=.01)
            except Exception as exc:errors.append(exc)
        thread=threading.Thread(target=run);thread.start()
        deadline=time.monotonic()+10
        while (not count.exists() or count.read_text()!=str(expected)) and time.monotonic()<deadline:time.sleep(.02)
        assert count.read_text()==str(expected)
        with pytest.raises(BlockingIOError):m.supervise(config,check=check,stop=threading.Event())
        stop.set();thread.join(5)
        assert not thread.is_alive() and not errors
        assert json.loads((Path(config['state_directory'])/'health.json').read_text())['status']=='stopped'


def test_wire_grant_arrays_validate_as_json(config,preflight_fixture,tmp_path):
    from stock_discovery_analysis.evidence_fixtures import evidence_grant
    _,conn=preflight_fixture
    put(tmp_path/'grants',json.dumps([evidence_grant().model_dump(mode='json')]))
    assert m.preflight(config,connect=lambda *a,**k:conn)[1]==12


def test_preflight_queries_are_bounded(config,preflight_fixture):
    _,conn=preflight_fixture
    def connect(*args,**kwargs):
        assert 'statement_timeout=15000' in kwargs['options']
        assert 'lock_timeout=2000' in kwargs['options']
        return conn
    m.preflight(config,connect=connect)


def test_stop_during_preflight_does_not_launch(config):
    stop=threading.Event()
    def check(_):stop.set();return m.environment(config),12
    m.supervise(config,check=check,stop=stop)
    assert json.loads((Path(config['state_directory'])/'health.json').read_text())['status']=='stopped'


def test_timeout_clean_exit_never_reports_success(config,monkeypatch):
    stop=threading.Event();states=[]
    class Child:
        pid=123;returncode=None
        def poll(self):return None
        def wait(self,timeout=None):self.returncode=0;return 0
    monkeypatch.setattr(m.subprocess,'Popen',lambda *a,**k:Child())
    monkeypatch.setattr(m.os,'killpg',lambda *a:None)
    def record(directory,status,**kwargs):
        states.append(status)
        if status=='cycle_timed_out':stop.set()
    monkeypatch.setattr(m,'state',record)
    m.supervise(config,check=lambda _:(m.environment(config),12),stop=stop,cycle_timeout=0)
    assert 'cycle_timed_out' in states and 'cycle_completed' not in states


def test_orphan_child_keeps_singleton_lock(config,tmp_path):
    import subprocess,signal,fcntl
    package=Path(config['repo'])/'worker/worker';(package/'__init__.py').write_text('')
    pidfile=tmp_path/'pid'
    (package/'main.py').write_text('import os,time\nfrom pathlib import Path\nPath('+repr(str(pidfile))+').write_text(str(os.getpid()))\ntime.sleep(2)\n')
    manifest=tmp_path/'config.json';manifest.write_text(json.dumps(config))
    code='import importlib.util,json; s=importlib.util.spec_from_file_location("c",'+repr(m.__file__)+'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); c=json.load(open('+repr(str(manifest))+')); m.supervise(c,check=lambda _:(m.environment(c),12))'
    parent=subprocess.Popen([sys.executable,'-c',code])
    try:
        deadline=time.monotonic()+10
        while not pidfile.exists() and time.monotonic()<deadline:time.sleep(.02)
        assert pidfile.exists()
        parent.kill();parent.wait(timeout=5)
        with (Path(config['state_directory'])/'consumer.lock').open('a') as lock:
            with pytest.raises(BlockingIOError):fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            deadline=time.monotonic()+5
            while True:
                try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);break
                except BlockingIOError:
                    assert time.monotonic()<deadline
                    time.sleep(.02)
    finally:
        if parent.poll() is None:parent.kill();parent.wait()
