"""Disposable PostgreSQL regression for the online transfer snapshot."""
import os,tempfile,threading,time,unittest
from pathlib import Path
from uuid import uuid4
from stk099_transfer import Database,backup_online,restore


@unittest.skipUnless(os.getenv('STK099_TEST_CONTAINER'),'isolated PostgreSQL container required')
class OnlineBackupPostgres(unittest.TestCase):
    def test_counter_writes_continue_and_snapshot_restores_exactly(self):
        name='stk099_online_'+uuid4().hex[:10]
        db=Database(os.environ['STK099_TEST_CONTAINER'],os.getenv('STK099_TEST_OWNER','postgres'),name,os.getenv('STK099_TEST_CONTEXT'))
        db.sql('CREATE DATABASE '+name,'postgres')
        db.sql("CREATE TABLE alembic_version(version_num text); INSERT INTO alembic_version VALUES ('0017'); CREATE TABLE changing_counter(n integer); INSERT INTO changing_counter VALUES (0)")
        stop=threading.Event();writes=[];errors=[]
        def update():
            try:
                while not stop.is_set():
                    db.sql('UPDATE changing_counter SET n=n+1');writes.append(1);time.sleep(.01)
            except Exception as exc:errors.append(type(exc).__name__)
        writer=threading.Thread(target=update);writer.start()
        with tempfile.TemporaryDirectory() as tmp:
            dump=Path(tmp)/'snapshot.dump';cluster=db.sql('SELECT system_identifier FROM pg_control_system()')
            try:manifest=backup_online(db,dump,cluster)
            finally:stop.set();writer.join(timeout=10)
            self.assertFalse(writer.is_alive());self.assertEqual(errors,[]);self.assertGreater(len(writes),1)
            self.assertNotEqual(db.snapshot(),manifest['snapshot'])
            target=Database(os.environ['STK099_TEST_CONTAINER'],db.owner,name+'_restore',os.getenv('STK099_TEST_CONTEXT'))
            self.assertEqual(restore(target,dump,manifest,db.owner,expected_source=name,expected_source_cluster=cluster),manifest['snapshot'])
