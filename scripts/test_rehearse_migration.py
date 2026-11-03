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


if __name__ == '__main__':
    unittest.main()
