"""Mandatory CI fan-in must reject failed, skipped and cancelled jobs."""
from pathlib import Path
import unittest
import yaml


class CIGates(unittest.TestCase):
    def test_required_jobs_and_fail_closed_aggregate(self):
        workflow=yaml.safe_load((Path(__file__).resolve().parents[1]/'.github/workflows/ci.yml').read_text())
        jobs=workflow['jobs']; gate=jobs['checks']
        self.assertEqual(set(gate['needs']),{'changes','unit','postgres','ui'})
        self.assertEqual(gate['if'],'${{ always() }}')
        step=gate['steps'][-1]
        self.assertEqual(step['env']['CI_NEEDS_JSON'],'${{ toJSON(needs) }}')
        self.assertEqual(step['run'],'python3 scripts/ci_select.py --gate')
        for name in ('unit','postgres','ui'):
            self.assertEqual(jobs[name]['needs'],'changes')
            self.assertEqual(jobs[name]['if'],"${{ needs.changes.outputs."+name+" == 'true' }}")
            self.assertEqual(jobs['changes']['outputs'][name],'${{ steps.select.outputs.'+name+' }}')
        selection=jobs['changes']['steps']
        self.assertEqual(selection[0]['with']['fetch-depth'],0)
        for command in ('test_ci_selection.py','scripts/ci_select.py','scripts/ci_docs.py'):
            matches=[s for s in selection if command in s.get('run','')]
            self.assertEqual(len(matches),1)
            self.assertNotIn('if',matches[0])
        self.assertEqual(workflow['concurrency'],{'group':'ci-${{ github.ref }}','cancel-in-progress':True})
        triggers=workflow.get('on',workflow.get(True))  # YAML 1.1 treats on as boolean.
        self.assertNotIn('paths',triggers['push']); self.assertNotIn('paths-ignore',triggers['push'])
        self.assertIsNone(triggers['pull_request'])
        for job in jobs.values():
            self.assertNotIn('continue-on-error',job)
            for item in job['steps']:self.assertNotIn('continue-on-error',item)

    def test_all_acceptance_commands_remain_required(self):
        workflow=yaml.safe_load((Path(__file__).resolve().parents[1]/'.github/workflows/ci.yml').read_text())
        required={
            'unit':['validate_contract_examples.py','validate_evaluation_examples.py','validate_capital_risk_examples.py',
                    'pytest backend/tests worker/tests --ignore=backend/tests/integration','worker.main --once','unittest discover'],
            'postgres':['scripts/validate_migrations.py','test_stk099_online_postgres.py'],
            'ui':['npm ci','npm run build','docker compose up --build','scripts/smoke_compose.py',
                  'scripts/capture_platform_licenses.py','npm run test:e2e',
                  'test_chartink_delivery.py','scripts/stk099_rehearsal.py'],
        }
        for job,commands in required.items():
            steps=workflow['jobs'][job]['steps']
            for command in commands:
                matches=[s for s in steps if command in s.get('run','')]
                self.assertEqual(len(matches),1,command)
                self.assertNotIn('if',matches[0])
