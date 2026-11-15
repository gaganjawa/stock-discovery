import json
from pathlib import Path
import tempfile
import unittest
from stk099_transfer import identifier, restore
from stk099_prepare import prepare


class TransferGuards(unittest.TestCase):
    def test_identifiers_and_existing_secret_dir(self):
        for bad in ['x;DROP DATABASE x','postgres.foo','', 'a-b']:
            with self.assertRaises(ValueError):identifier(bad)
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'secrets';prepare(target)
            before=(target/'worker_url').read_bytes()
            with self.assertRaises(FileExistsError):prepare(target)
            self.assertEqual((target/'worker_url').read_bytes(),before)
            self.assertEqual(target.stat().st_mode & 0o777,0o700)
            self.assertIn('NOBYPASSRLS', (target/'bootstrap.sql').read_text())

    def test_checksum_failure_never_contacts_target(self):
        class DB:
            def sql(self,*args):raise AssertionError('must not contact database')
        with tempfile.TemporaryDirectory() as tmp:
            dump=Path(tmp)/'dump';dump.write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError,'checksum'):
                restore(DB(),dump,{'sha256':'wrong'},'owner')

    def test_restore_identity_and_cross_cluster_guards(self):
        from stk099_transfer import checksum
        class DB:
            name='isolated';owner='owner'
            def __init__(self):self.calls=[];self.exists=False
            def sql(self,*args):
                self.calls.append(args)
                if self.exists:raise RuntimeError('exists')
            def run(self,*args,**kwargs):self.calls.append('restore')
            def snapshot(self):return {'revision':'0016'}
        with tempfile.TemporaryDirectory() as tmp:
            dump=Path(tmp)/'dump';dump.write_bytes(b'dump')
            manifest=dict(source='source_db',cluster='source_cluster',sha256=checksum(dump),snapshot={'revision':'0016'})
            for source,cluster in [(None,None),('source_db',None),(None,'source_cluster'),('wrong','source_cluster'),('source_db','wrong')]:
                db=DB()
                with self.assertRaises(ValueError):restore(db,dump,manifest,'owner',expected_source=source,expected_source_cluster=cluster)
                self.assertEqual(db.calls,[])
            args=dict(expected_source='source_db',expected_source_cluster='source_cluster')
            db=DB();self.assertEqual(restore(db,dump,manifest,'owner',**args),manifest['snapshot'])
            self.assertEqual(len(db.calls),2) # No destination-cluster equality query.
            db=DB();db.name='chartink_inbox'
            with self.assertRaisesRegex(ValueError,'protected'):restore(db,dump,manifest,'owner',**args)
            self.assertEqual(db.calls,[])
            db=DB();db.exists=True
            with self.assertRaisesRegex(RuntimeError,'exists'):restore(db,dump,manifest,'owner',**args)
            self.assertEqual(len(db.calls),1)

    def test_backup_supports_only_reviewed_pre_and_post_migration_schemas(self):
        from stk099_transfer import backup
        class DB:
            name='synthetic';owner='synthetic'
            def __init__(self,revision):self.revision=revision
            def sql(self,*args):return 'synthetic-cluster'
            def snapshot(self):return {'revision':self.revision,'tables':{},'sequences':{}}
            def run(self,args,stdout):stdout.write(b'synthetic-dump')
        with tempfile.TemporaryDirectory() as tmp:
            for revision in ('0016','0017'):
                manifest=backup(DB(revision),Path(tmp)/revision,'synthetic-cluster')
                self.assertEqual(manifest['snapshot']['revision'],revision)
            for revision in ('0015','0018'):
                with self.assertRaisesRegex(ValueError,'supported_schema'):
                    backup(DB(revision),Path(tmp)/revision,'synthetic-cluster')

    def test_online_backup_pins_dump_and_fails_on_sequence_change(self):
        from contextlib import contextmanager
        from stk099_transfer import backup_online
        class DB:
            name='synthetic';owner='synthetic'
            def __init__(self,changed):self.changed=changed;self.reads=0;self.active=False
            def sql(self,*args):return 'synthetic-cluster'
            @contextmanager
            def exported_snapshot(self):
                self.active=True
                try:yield '00000001-00000002-1'
                finally:self.active=False
            def snapshot(self,snapshot):
                assert self.active and snapshot=='00000001-00000002-1'
                self.reads+=1
                return {'revision':'0017','tables':{},'sequences':{'seq':2 if self.changed and self.reads>1 else 1}}
            def run(self,args,stdout):
                assert self.active and args[-2:]==['--snapshot','00000001-00000002-1']
                stdout.write(b'synthetic-dump')
        with tempfile.TemporaryDirectory() as tmp:
            good=DB(False);target=Path(tmp)/'good.dump'
            self.assertEqual(backup_online(good,target,'synthetic-cluster')['backup_mode'],'exported_read_only_snapshot')
            self.assertFalse(good.active)
            changed=DB(True);target=Path(tmp)/'changed.dump'
            with self.assertRaisesRegex(ValueError,'sequence_or_schema_changed'):
                backup_online(changed,target,'synthetic-cluster')
            self.assertFalse(changed.active)
            self.assertFalse(target.with_suffix('.manifest.json').exists())

    def test_optional_refresh_credential_is_separate_without_provider_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'secrets';prepare(target,price_refresh=True)
            self.assertIn('stk_price_refresh:',(target/'refresh_url').read_text())
            self.assertNotEqual((target/'refresh_url').read_text(),(target/'worker_url').read_text())
            self.assertFalse((target/'upstox_token').exists())
