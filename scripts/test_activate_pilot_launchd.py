import plistlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from activate_pilot_launchd import APPROVAL, activate, agent_path, deactivate, status
from prepare_pilot_launchd import definition


class Runner:
    def __init__(self, code=0, stdout=''):self.calls=[];self.code=code;self.stdout=stdout
    def __call__(self, args, **kw):self.calls.append(args);return SimpleNamespace(returncode=self.code, stdout=self.stdout)


class ActivateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();root = Path(self.tmp.name)
        for name in ('python', 'pilot.json', 'schedule.json', 'database'):(root / name).touch()
        (root / 'ops').mkdir()
        self.reviewed = root / 'reviewed.plist'
        self.reviewed.write_bytes(plistlib.dumps(definition(root / 'python', root, root / 'pilot.json', root / 'schedule.json', root / 'database', root / 'ops')))
        self.home = root / 'home'

    def tearDown(self):self.tmp.cleanup()

    def test_activation_requires_phrase_and_current_schema(self):
        run = Runner()
        with self.assertRaises(PermissionError):activate(self.reviewed, 'yes', home=self.home, run=run, schema=lambda f: '0015', uid=501)
        with self.assertRaisesRegex(ValueError, 'database_migration_required'):
            activate(self.reviewed, APPROVAL, home=self.home, run=run, schema=lambda f: '0013', uid=501)
        self.assertEqual(run.calls, []);self.assertFalse(agent_path(self.home).exists())
        result = activate(self.reviewed, APPROVAL, home=self.home, run=run, schema=lambda f: '0015', uid=501)
        self.assertEqual(result['status'], 'active')
        self.assertEqual(run.calls, [['launchctl', 'bootstrap', 'gui/501', str(agent_path(self.home))]])
        self.assertEqual(agent_path(self.home).stat().st_mode & 0o777, 0o600)
        with self.assertRaises(FileExistsError):activate(self.reviewed, APPROVAL, home=self.home, run=run, schema=lambda f: '0015', uid=501)

    def test_failed_bootstrap_leaves_nothing_installed_and_stop_removes_agent(self):
        with self.assertRaisesRegex(RuntimeError, 'bootstrap_failed'):
            activate(self.reviewed, APPROVAL, home=self.home, run=Runner(code=5), schema=lambda f: '0015', uid=501)
        self.assertFalse(agent_path(self.home).exists())
        activate(self.reviewed, APPROVAL, home=self.home, run=Runner(), schema=lambda f: '0015', uid=501)
        run = Runner()
        self.assertEqual(deactivate(home=self.home, run=run, uid=501)['status'], 'inactive')
        self.assertEqual(run.calls, [['launchctl', 'bootout', 'gui/501/local.stock-discovery.research']])
        self.assertFalse(agent_path(self.home).exists())

    def test_status_reports_only_safe_fields(self):
        out = 'state = running\nruns = 3\nlast exit code = 0\nenvironment = {\n DATABASE_URL_FILE = /private\n}'
        self.assertEqual(status(run=Runner(stdout=out), uid=501), dict(status='active', label='local.stock-discovery.research', state='running', runs='3', last_exit='0'))
        self.assertEqual(status(run=Runner(code=113), uid=501)['status'], 'inactive')


if __name__ == '__main__':unittest.main()
