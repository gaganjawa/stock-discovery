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
