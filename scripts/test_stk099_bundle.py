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

    def test_missing_and_intentionally_empty_sources(self):
        for kind in ('absent','file','empty','valid_empty'):
            for allow in (False,True):
                with self.subTest(kind=kind,allow=allow),tempfile.TemporaryDirectory() as tmp:
                    root=Path(tmp);g=root/'grants';g.write_text('[]')
                    view=root/'view';view.write_text(json.dumps(dict(sources=dict(grant_file=str(g),retention_days=30),listing_ids=['NSE:SYN'])))
                    watch=root/'watch'
                    if kind=='file':watch.write_text('not a directory')
                    elif kind!='absent':watch.mkdir()
                    if kind=='valid_empty':(watch/'watchlist.json').write_bytes(b'{}\n')
                    if kind=='valid_empty' or kind=='empty' and allow:
                        bundle(view,watch,root/'out',allow_empty_watchlist=allow)
                        audit=json.loads((root/'out/watchlist-export.json').read_text())
                        self.assertEqual(audit['intentionally_empty'],kind=='empty')
                        if kind=='valid_empty':self.assertEqual((root/'out/watchlist/watchlist.json').read_bytes(),b'{}\n')
                    else:
                        with self.assertRaises(ValueError):bundle(view,watch,root/'out',allow_empty_watchlist=allow)
                        self.assertFalse((root/'out').exists())

    def test_changed_deleted_or_created_during_copy_cannot_complete(self):
        from unittest.mock import patch
        for change in ('changed','deleted','created'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);g=root/'grants';g.write_text('[]')
                view=root/'view';view.write_text(json.dumps(dict(sources=dict(grant_file=str(g),retention_days=30),listing_ids=['NSE:SYN'])))
                watch=root/'watch';watch.mkdir();source=watch/'watchlist.json'
                if change!='created':source.write_text('{}')
                original=Path.write_bytes
                def racing_write(path,data):
                    if path.name=='original-view.json':
                        if change=='deleted':source.unlink()
                        else:source.write_text('{"changed":true}')
                    return original(path,data)
                with patch.object(Path,'write_bytes',racing_write),self.assertRaises((ValueError,OSError)):
                    bundle(view,watch,root/'out',allow_empty_watchlist=change=='created')
                self.assertFalse((root/'out/files.sha256.json').exists())
