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
