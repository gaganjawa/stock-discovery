"""STK-099 operations safety using isolated synthetic transports and databases."""
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch

import operate
import stk099_transfer as transfer


class OnlineOperationsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.state=self.root/'state';self.state.mkdir()
        self.key=self.root/'key';self.key.write_text('synthetic-password');self.key.chmod(0o600)
        self.bundle=self.root/'bundle';self.bundle.write_bytes(b'synthetic-config-watchlist');self.bundle.chmod(0o600)
        self.config={'scope':'receiver','off_server_confirmed':True,'separate_key_custody_confirmed':True,
                     'repository_id':'a'*64,'bundle_sha256':transfer.checksum(self.bundle),
                     'sources':[{'database':'chartink_inbox','container':'synthetic-source','owner':'owner','cluster':'111','restore_owner':'owner'}],
                     'recovery':{'container':'synthetic-target','owner':'owner','cluster':'222'}}
        self.path=self.root/'config.json';self.write_config()
        self.env={'STK099_TRANSFER_CONFIG':str(self.path),'RESTIC_PASSWORD_FILE':str(self.key),
                  'RESTIC_REPOSITORY':'s3:https://backup.invalid/synthetic','STK_RECOVERY_BUNDLE':str(self.bundle),'CODE_VERSION':'synthetic'}
        self.transport=[];self.database_calls=[]

    def write_config(self):
        self.path.write_text(json.dumps(self.config));self.path.chmod(0o600)

    def database(self,container,owner,name):
        calls=self.database_calls
        class DB:
            def __init__(self):self.name=name;self.owner=owner
            def sql(self,query):
                calls.append(query);return '222' if container=='synthetic-target' else '111'
            def run(self,args,stdout):
                calls.append(args);stdout.write(b'-- synthetic roles')
        return DB()

    def backup(self,db,path,cluster):
        path.write_bytes(b'synthetic-dump')
        manifest={'source':db.name,'cluster':cluster,'sha256':transfer.checksum(path),'snapshot':{'revision':'0018','tables':{'discovery.test':{'rows':1}},'sequences':{}}}
        path.with_suffix('.manifest.json').write_text(json.dumps(manifest));return manifest

    def restic(self,*args):
        self.transport.append(args)
        if args==('--no-cache','cat','config'):return json.dumps({'id':'a'*64}).encode()
        if args[0]=='backup':return b'{"message_type":"summary","snapshot_id":"bbbbbbbb"}\n'
        if args[:2]==('--no-cache','restore'):
            target=Path(args[-1])/self.state.relative_to(self.state.anchor)/'stage'
            shutil.copytree(self.state/'stage',target)
            return b''
        raise AssertionError(args)

    def context(self):
        from contextlib import ExitStack
        stack=ExitStack();stack.enter_context(patch.dict(os.environ,self.env,clear=True))
        stack.enter_context(patch.object(transfer,'Database',side_effect=self.database))
        stack.enter_context(patch.object(transfer,'backup_online',side_effect=self.backup))
        self.restorer=stack.enter_context(patch.object(transfer,'restore',return_value={}))
        self.runner=stack.enter_context(patch.object(operate,'run'))
        stack.enter_context(patch.object(operate,'restic',side_effect=self.restic))
        stack.enter_context(patch.object(operate,'notify'))
        return stack

    def test_online_cycle_restores_exact_remote_snapshot_without_service_commands(self):
        with self.context():operate.backup_cycle(self.state)
        receipt=json.loads((self.state/'last-backup.json').read_text())
        self.assertEqual(receipt['scope'],'receiver');self.assertEqual(receipt['snapshot'],'bbbbbbbb')
        self.runner.assert_not_called();self.assertEqual(self.restorer.call_count,1)
        self.assertEqual(self.restorer.call_args.kwargs,{'expected_source':'chartink_inbox','expected_source_cluster':'111'})
        self.assertTrue(any(x[:3]==('--no-cache','restore','bbbbbbbb') for x in self.transport))
        self.assertEqual(list((self.state/'stage').iterdir()),[])
        self.assertFalse(any('prune' in x or 'forget' in x for x in self.transport))

    def test_unsupported_schema_never_uploads_or_claims_recovery(self):
        original=self.backup
        for revision in ('0017','0019'):
            with self.subTest(revision=revision):
                def unsupported(*args):
                    result=original(*args);result['snapshot']['revision']=revision;return result
                with self.context(),patch.object(transfer,'backup_online',side_effect=unsupported),self.assertRaisesRegex(ValueError,'schema_0018_required'):
                    operate.backup_cycle(self.state)
                self.assertFalse(any(args[0]=='backup' for args in self.transport))
                self.assertFalse((self.state/'last-backup.json').exists())
                shutil.rmtree(self.state/'stage')

    def test_same_cluster_recovery_is_rejected_before_backup(self):
        self.config['recovery']['cluster']='111';self.write_config()
        with self.context(),self.assertRaisesRegex(ValueError,'independent'):operate.backup_cycle(self.state)
        self.assertFalse((self.state/'stage').exists())

    def test_repository_and_custody_required(self):
        for field in ('off_server_confirmed','separate_key_custody_confirmed'):
            self.config[field]=False;self.write_config()
            with self.context(),self.assertRaisesRegex(ValueError,'confirmation'):operate.backup_cycle(self.state)
            self.config[field]=True
        self.env['RESTIC_REPOSITORY']='/same-host/repo';self.write_config()
        with self.context(),self.assertRaisesRegex(ValueError,'remote_encrypted'):operate.backup_cycle(self.state)

    def test_restored_corruption_keeps_failed_stage_and_no_receipt(self):
        original=self.restic
        def corrupt(*args):
            result=original(*args)
            if args[:2]==('--no-cache','restore'):
                (Path(args[-1])/self.state.relative_to(self.state.anchor)/'stage/recovery.bundle').write_bytes(b'bad')
            return result
        with self.context(),patch.object(operate,'restic',side_effect=corrupt),self.assertRaisesRegex(ValueError,'recovered_file'):
            operate.backup_cycle(self.state)
        self.assertFalse((self.state/'last-backup.json').exists());self.assertTrue((self.state/'stage/manifest.json').exists())
        self.restorer.assert_not_called()

    def test_recovery_failure_preserves_previous_receipt(self):
        (self.state/'last-backup.json').write_text('{"previous":true}')
        with self.context(),patch.object(transfer,'restore',side_effect=ValueError('restore failure')),self.assertRaises(ValueError):
            operate.backup_cycle(self.state)
        self.assertEqual(json.loads((self.state/'last-backup.json').read_text()),{'previous':True})

    def test_hosted_scope_requires_both_databases(self):
        self.config['scope']='hosted';self.write_config()
        with self.context(),self.assertRaisesRegex(ValueError,'scope_mismatch'):operate.backup_cycle(self.state)

    def test_changed_bundle_or_repository_and_insecure_key_fail(self):
        self.config['bundle_sha256']='b'*64;self.write_config()
        with self.context(),self.assertRaisesRegex(ValueError,'bundle_changed'):operate.backup_cycle(self.state)
        self.config['bundle_sha256']=transfer.checksum(self.bundle);self.config['repository_id']='b'*64;self.write_config()
        with self.context(),self.assertRaisesRegex(ValueError,'repository_identity'):operate.backup_cycle(self.state)
        self.key.chmod(0o644)
        with self.context(),self.assertRaisesRegex(ValueError,'private_backup'):operate.backup_cycle(self.state)


class MonitoringTests(unittest.TestCase):
    def test_receiver_monitor_never_queries_absent_application_tables(self):
        with tempfile.TemporaryDirectory() as root:
            state=Path(root)
            rows=[{'Service':name,'State':'running','Health':'healthy'} for name in ('database','receiver','proxy')]
            with patch.dict(os.environ,{'STK_MONITOR_MODE':'receiver'},clear=True),patch.object(operate,'run',return_value=json.dumps(rows).encode()),patch.object(operate,'command',return_value=b'0018\n') as query,patch.object(operate,'notify'):
                self.assertFalse(operate.monitor(state))
            codes=json.loads((state/'monitor.json').read_text())['codes']
            self.assertNotIn('receiver_schema_unexpected',codes);self.assertIn('backup_unverified',codes);self.assertIn('external_alert_unconfigured',codes)
            self.assertFalse(any(x.startswith(('api_','worker_','web_','queue_')) for x in codes))
            self.assertEqual(query.call_args.kwargs['input'],b'SELECT version_num FROM public.alembic_version;')

    def test_alert_drill_requires_hook_and_never_claims_external_delivery(self):
        with tempfile.TemporaryDirectory() as root:
            state=Path(root)
            with patch.dict(os.environ,{},clear=True),self.assertRaisesRegex(ValueError,'hook_required'):operate.alert_test(state)
            hook=state/'hook';hook.write_text('test');hook.chmod(0o700)
            with patch.dict(os.environ,{'STK_ALERT_EXECUTABLE':str(hook)},clear=True),patch.object(operate,'run',return_value=b'') as run:
                operate.alert_test(state)
            self.assertEqual(json.loads(run.call_args.kwargs['input'])['event'],'release_alert_test')
            self.assertFalse(json.loads((state/'last-alert-test.json').read_text())['external_delivery_verified'])

    def test_failed_alert_is_not_acknowledged(self):
        with tempfile.TemporaryDirectory() as root:
            state=Path(root);hook=state/'hook';hook.write_text('test');hook.chmod(0o700)
            with (patch.dict(os.environ,{'STK_ALERT_EXECUTABLE':str(hook)},clear=True),
                  patch.object(operate,'run',side_effect=OSError('transport')),
                  self.assertRaises(OSError)):
                operate.alert_test(state)
            self.assertFalse((state/'last-alert-test.json').exists())

    def test_hosted_monitor_rejects_receiver_only_backup_and_checks_both_queues(self):
        with tempfile.TemporaryDirectory() as root:
            state=Path(root)
            (state/'last-backup.json').write_text(json.dumps({'verified_at':time.time(),'scope':'receiver'}))
            rows=[{'Service':name,'State':'running','Health':'healthy'} for name in ('database','receiver','proxy','api','worker','web','price-refresh')]
            with (patch.dict(os.environ,{'STK_MONITOR_MODE':'hosted'},clear=True),
                  patch.object(operate,'run',return_value=json.dumps(rows).encode()),
                  patch.object(operate,'command',side_effect=[b'0|0',b'1|1']) as query,
                  patch.object(operate,'notify')):
                self.assertFalse(operate.monitor(state))
            codes=json.loads((state/'monitor.json').read_text())['codes']
            self.assertIn('backup_scope_mismatch',codes)
            self.assertIn('jobs_failed',codes);self.assertIn('jobs_stale',codes)
            self.assertEqual(query.call_count,2)
            self.assertIn(b'discovery.schedule_jobs',query.call_args.kwargs['input'])
            self.assertEqual(query.call_args.args[1],'stk_real001_private')

    def test_release_mode_never_falls_back_to_stopping_services(self):
        with tempfile.TemporaryDirectory() as root:
            with (patch.dict(os.environ,{'STK_MONITOR_MODE':'receiver'},clear=True),
                  patch.object(operate,'run') as run,
                  self.assertRaisesRegex(ValueError,'online_transfer_config_required')):
                operate.backup_cycle(Path(root))
            run.assert_not_called()
