import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import operate


class BackupFailureTests(unittest.TestCase):
    def test_dump_failure_restarts_writers_and_never_prunes(self):
        with tempfile.TemporaryDirectory() as root:
            state = Path(root)
            key = state / "key"; key.write_text("test-only"); key.chmod(0o600)
            with patch.dict(os.environ, {"RESTIC_REPOSITORY": str(state / "repo"), "RESTIC_PASSWORD_FILE": str(key)}), \
                 patch.object(operate, "run") as run, patch.object(operate, "restic") as restic, \
                 patch.object(operate, "backup", side_effect=RuntimeError("dump failed")):
                with self.assertRaises(RuntimeError): operate.backup_cycle(state)
                self.assertEqual(run.call_args_list[-1].args[0][-3:], ["start", "api", "worker"])
                restic.assert_not_called()
                self.assertFalse((state / "last-backup.json").exists())

    def test_retention_requires_explicit_owner_authorization(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {"STK_PRUNE_AUTHORIZED": "false"}), patch.object(operate, "restic") as restic:
            with self.assertRaises(ValueError): operate.prune(Path(root))
            restic.assert_not_called()

    def test_remote_recovery_failure_never_expires_backups(self):
        with tempfile.TemporaryDirectory() as root:
            state = Path(root)
            key = state / "key"; key.write_text("test-only"); key.chmod(0o600)
            def fake_backup(path, verify):
                path.write_bytes(b"dump")
                return {"schema": "0004", "research_tables": {}, "sha256": "fake"}
            def fake_restic(*args):
                if args[0] == "backup": return b'{"message_type":"summary","snapshot_id":"abc"}\n'
                raise RuntimeError("restore failed")
            with patch.dict(os.environ, {"RESTIC_REPOSITORY": str(state / "repo"), "RESTIC_PASSWORD_FILE": str(key), "CODE_VERSION": "test"}), \
                 patch.object(operate, "run", return_value=b""), patch.object(operate, "backup", side_effect=fake_backup), \
                 patch.object(operate, "restic", side_effect=fake_restic) as restic:
                with self.assertRaises(RuntimeError): operate.backup_cycle(state)
                self.assertEqual([call.args[0] for call in restic.call_args_list], ["backup", "restore"])
                self.assertFalse((state / "last-backup.json").exists())
                self.assertFalse((state / "stage/database.dump").exists())


if __name__ == "__main__": unittest.main()
