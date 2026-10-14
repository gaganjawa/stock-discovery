import tempfile
import unittest
from pathlib import Path
from local import prepare


class LocalSetupTests(unittest.TestCase):
    def test_generates_private_owner_key_and_preserves_existing_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'.env.example').write_text('AUTH_TOKEN=\nOPENAI_API_KEY=\nLLM_ENABLED=false\n')
            prepare(root)
            first=(root/'.env').read_text()
            key=next(line.split('=',1)[1] for line in first.splitlines() if line.startswith('AUTH_TOKEN='))
            self.assertGreaterEqual(len(key),32)
            prepare(root)
            self.assertEqual((root/'.env').read_text(),first)
            self.assertEqual((root/'.env').stat().st_mode & 0o777,0o600)

    def test_does_not_replace_existing_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            original='AUTH_TOKEN=existing-owner\nOPENAI_API_KEY=existing-placeholder\nWEB_PORT=5180\n'
            (root/'.env').write_text(original)
            self.assertEqual(prepare(root)['WEB_PORT'],'5180')
            self.assertEqual((root/'.env').read_text(),original)
