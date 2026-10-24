import tempfile
import unittest
from pathlib import Path
from prepare_pilot_launchd import definition


class LaunchdTests(unittest.TestCase):
    def test_preview_keeps_venv_interpreter_path_and_contains_no_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);real=root/'python-real';real.touch();link=root/'venv-python';link.symlink_to(real)
            result=definition(link,root,real,real,real,root)
            self.assertEqual(result['ProgramArguments'][0],str(link))
            self.assertTrue(result['KeepAlive'])
            self.assertEqual(result['ThrottleInterval'],60)
            self.assertNotIn('DATABASE_URL',result['EnvironmentVariables'])
            self.assertEqual(result['StandardOutPath'],'/dev/null')
