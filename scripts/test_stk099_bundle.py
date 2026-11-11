import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from stk099_bundle import bundle


class BundleTests(unittest.TestCase):
    def test_original_bytes_and_watchlist_preserved_paths_only_remapped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);grants=root/'grants';grants.write_text('[]\n')
            watch=root/'watch';watch.mkdir();(watch/'watchlist.json').write_text('{"SYN": {"note":"keep"}}\n')
            view=root/'view';original=json.dumps(dict(sources=dict(grant_file=str(grants),retention_days=30),listing_ids=['NSE:SYN']))
            view.write_text(original)
            bundle(view,watch,root/'bundle')
            self.assertEqual(view.read_text(),original)
            self.assertEqual((root/'bundle/watchlist/watchlist.json').read_bytes(),(watch/'watchlist.json').read_bytes())
            migrated=json.loads((root/'bundle/private/view.json').read_text())
            self.assertEqual(migrated['sources']['grant_file'],'/run/private/grants.json')
            self.assertEqual(migrated['sources']['retention_days'],30)
            for name,digest in json.loads((root/'bundle/files.sha256.json').read_text()).items():
                self.assertEqual(hashlib.sha256((root/'bundle'/name).read_bytes()).hexdigest(),digest)
            with self.assertRaises(FileExistsError):bundle(view,watch,root/'bundle')
