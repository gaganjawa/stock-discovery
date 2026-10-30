"""Mandatory CI fan-in must reject failed, skipped and cancelled jobs."""
import itertools
from pathlib import Path
import subprocess
import unittest
import yaml


class CIGates(unittest.TestCase):
    def test_required_jobs_and_fail_closed_aggregate(self):
        workflow=yaml.safe_load((Path(__file__).resolve().parents[1]/'.github/workflows/ci.yml').read_text())
        jobs=workflow['jobs']; gate=jobs['checks']
        self.assertEqual(set(gate['needs']),{'unit','postgres','ui'})
        self.assertEqual(gate['if'],'${{ always() }}')
        step=gate['steps'][0]
        for name in gate['needs']:
            self.assertEqual(step['env'][name.upper()+'_RESULT'],'${{ needs.'+name+'.result }}')
        for results in itertools.product(('success','failure','cancelled','skipped'),repeat=3):
            env=dict(zip(('UNIT_RESULT','POSTGRES_RESULT','UI_RESULT'),results))
            code=subprocess.run(['bash','-e','-c',step['run']],env=env,capture_output=True).returncode
            self.assertEqual(code==0,all(r=='success' for r in results),results)
        for job in jobs.values():
            self.assertNotIn('continue-on-error',job)
            for item in job['steps']:self.assertNotIn('continue-on-error',item)

    def test_all_acceptance_commands_remain_required(self):
        workflow=yaml.safe_load((Path(__file__).resolve().parents[1]/'.github/workflows/ci.yml').read_text())
        required={
            'unit':['validate_contract_examples.py','validate_evaluation_examples.py','validate_capital_risk_examples.py',
                    'pytest backend/tests worker/tests --ignore=backend/tests/integration','worker.main --once','unittest discover'],
            'postgres':['scripts/validate_migrations.py'],
            'ui':['npm ci','npm run build','docker compose up --build','scripts/smoke_compose.py',
                  'scripts/capture_platform_licenses.py','npm run test:e2e'],
        }
        for job,commands in required.items():
            steps=workflow['jobs'][job]['steps']
            for command in commands:
                matches=[s for s in steps if command in s.get('run','')]
                self.assertEqual(len(matches),1,command)
                self.assertNotIn('if',matches[0])
