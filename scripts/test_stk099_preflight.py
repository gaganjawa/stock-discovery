import unittest
from stk099_preflight import assess, MIB


class PreflightTests(unittest.TestCase):
    def test_fail_closed_and_budget(self):
        self.assertEqual(assess({})['static_budget'],'NO_GO')
        good=dict(memory_total=2048*MIB,memory_available=1000*MIB,cpus=2,
                  disk_free=8*1024**3,public_database_ports=False)
        self.assertEqual(assess(good)['static_budget'],'PASS')
        for key,value in [('memory_total',1024*MIB),('memory_available',200*MIB),
                          ('cpus',1),('disk_free',1024**3),('public_database_ports',True),
                          ('swap_used',512*MIB),('oom_kills',1)]:
            with self.subTest(key=key):
                self.assertEqual(assess({**good,key:value})['static_budget'],'NO_GO')
        self.assertTrue(assess(good)['deployment'].startswith('NO_GO'))
