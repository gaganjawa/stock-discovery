import unittest
from rehearse_migration import compare


class CompareTest(unittest.TestCase):
    def test_changed_rows_fail_and_added_tables_are_listed(self):
        before = {'a.x': dict(rows=1, sha256='1'), 'a.y': dict(rows=2, sha256='2')}
        self.assertEqual(compare(before, {**before, 'a.z': dict(rows=0, sha256='0')}),
                         dict(unchanged=True, changed=[], added=['a.z']))
        result = compare(before, {**before, 'a.y': dict(rows=2, sha256='3')})
        self.assertFalse(result['unchanged'])
        self.assertEqual(result['changed'], ['a.y'])
        self.assertFalse(compare(before, {'a.x': before['a.x']})['unchanged'])




class TargetTests(unittest.TestCase):
    def test_target_challenge_fails_closed_and_unlocks(self):
        from rehearse_migration import verify_target
        class Conn:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def execute(self,sql,args):calls.append(sql)
        for answer in (b'f\n',b'',b'garbage'):
            calls=[]
            with self.assertRaisesRegex(ValueError,'database_target_mismatch'):
                verify_target('dbname=synthetic',run=lambda *args:answer,connect=lambda *a,**k:Conn())
            self.assertIn('pg_advisory_unlock',calls[-1])
        calls=[]
        verify_target('dbname=synthetic',run=lambda *args:b't\n',connect=lambda *a,**k:Conn())
        self.assertEqual(len(calls),2)

    def test_mismatch_stops_before_dump_or_create(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        import rehearse_migration as module
        with tempfile.TemporaryDirectory() as directory:
            dest=Path(directory)/'backup.dump'
            with patch('sys.argv',['review',str(dest)]),patch.object(module,'database_url',return_value='dbname=synthetic'),patch.object(module,'verify_target',side_effect=ValueError('database_target_mismatch')),patch.object(module,'command') as command,patch('psycopg.connect',side_effect=AssertionError('unverified target accessed')):
                with self.assertRaisesRegex(ValueError,'database_target_mismatch'):module.main()
                command.assert_not_called()
                self.assertFalse(dest.exists())


if __name__ == '__main__':unittest.main()
