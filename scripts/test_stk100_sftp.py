"""STK-100 synthetic SFTP policy tests; no SSH, provider or filesystem writes remotely."""
import io
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from stk100_sftp import BrowserError, Config, ReadOnlyBrowser, DEFAULT_ROOT, MAX_BYTES, MAX_LINES, MAX_ENTRIES, ssh_text
from stk100_browser import arguments


def attrs(name='',mode=stat.S_IFDIR|0o755,size=0,uid=0):
    return SimpleNamespace(filename=name,st_mode=mode,st_size=size,st_mtime=1700000000,st_uid=uid,st_gid=0)


class FakeSFTP:
    def __init__(self):
        self.nodes={p:attrs() for p in ('/opt','/opt/stock-discovery','/opt/stock-discovery/deploy',DEFAULT_ROOT)}
        self.contents={};self.calls=[];self.entries=[];self.canonical=None;self.changed=False;self.yielded=0
    def file(self,name,body):
        p=DEFAULT_ROOT+'/'+name;self.nodes[p]=attrs(name,stat.S_IFREG|0o644,len(body));self.contents[p]=body
    def lstat(self,path):self.calls.append(('lstat',path));return self.nodes[path]
    def normalize(self,path):return self.canonical or path
    def listdir_iter(self,path,read_aheads):
        assert read_aheads==1
        for item in self.entries:self.yielded+=1;yield item
    def open(self,path,mode):
        assert mode=='rb';self.calls.append(('open',path,mode));parent=self
        class Handle(io.BytesIO):
            def stat(self):
                info=parent.nodes[path]
                if parent.changed and self.tell():return attrs(mode=info.st_mode,size=info.st_size+1)
                return info
            def read(self,size=-1):
                assert 0<=size<=MAX_BYTES
                parent.calls.append(('read',size))
                return super().read(size)
        return Handle(self.contents[path])


class PolicyTests(unittest.TestCase):
    def setUp(self):self.sftp=FakeSFTP();self.browser=ReadOnlyBrowser(self.sftp,(DEFAULT_ROOT,))

    def test_paths_secrets_and_symlinks_denied_before_open(self):
        for name in ('../etc/passwd','/etc/passwd','.env','prod.env.json','secrets.json','api-key.txt','cookies.txt','aws-access-key.json','id_ed25519','foo/../x','dir\\x','owner_url','private/log.txt'):
            with self.subTest(name=name),self.assertRaises(BrowserError):self.browser.preview(DEFAULT_ROOT,name)
        self.assertFalse(any(c[0]=='open' for c in self.sftp.calls))
        for path in ('/opt',DEFAULT_ROOT,DEFAULT_ROOT+'/link.txt'):
            old=self.sftp.nodes.get(path);self.sftp.nodes[path]=attrs(mode=stat.S_IFLNK|0o777)
            with self.assertRaisesRegex(BrowserError,'Symlinks'):self.browser.preview(DEFAULT_ROOT,'link.txt')
            if old:self.sftp.nodes[path]=old
        with self.assertRaises(BrowserError):self.browser.listing('/opt/stock-discovery-evil')

    def test_canonical_escape_and_untrusted_writers_denied(self):
        self.sftp.canonical='/etc'
        with self.assertRaisesRegex(BrowserError,'Canonical'):self.browser.listing(DEFAULT_ROOT)
        self.sftp.canonical=None
        for mode,uid in ((stat.S_IFDIR|0o777,0),(stat.S_IFDIR|0o755,1000)):
            self.sftp.nodes[DEFAULT_ROOT]=attrs(mode=mode,uid=uid)
            with self.assertRaisesRegex(BrowserError,'root-owned'):self.browser.listing(DEFAULT_ROOT)

    def test_listing_is_bounded_and_private_names_are_not_returned(self):
        self.sftp.entries=[attrs('.env'),attrs('secrets.json'),attrs('link',stat.S_IFLNK|0o777),attrs('README.md',stat.S_IFREG|0o644)]
        rows,limited=self.browser.listing(DEFAULT_ROOT)
        self.assertEqual([r['name'] for r in rows],['README.md']);self.assertFalse(limited)
        self.assertIn('+00:00',rows[0]['modified'])
        self.sftp.entries=[attrs('entry'+str(i)) for i in range(10000)];self.sftp.yielded=0
        rows,limited=self.browser.listing(DEFAULT_ROOT)
        self.assertTrue(limited);self.assertEqual(len(rows),MAX_ENTRIES);self.assertEqual(self.sftp.yielded,MAX_ENTRIES+1)

    def test_preview_json_text_and_log_tail_are_bounded(self):
        self.sftp.file('sample.json',b'{"status":"ok","count":3}')
        result=self.browser.preview(DEFAULT_ROOT,'sample.json')
        self.assertEqual(result['language'],'json');self.assertIn('"count": 3',result['text'])
        self.sftp.file('output.log',b'line\n'*(MAX_BYTES//2))
        result=self.browser.preview(DEFAULT_ROOT,'output.log')
        self.assertTrue(result['truncated']);self.assertGreater(result['offset'],0)
        self.assertLessEqual(len(result['text'].splitlines()),MAX_LINES)
        self.assertEqual(result['bytes_read'],MAX_BYTES)
        self.sftp.file('large.txt',b'x '*(MAX_BYTES*2))
        self.assertTrue(self.browser.preview(DEFAULT_ROOT,'large.txt')['truncated'])
        self.assertTrue(all(c[2]=='rb' for c in self.sftp.calls if c[0]=='open'))

    def test_sensitive_content_binary_and_special_files_are_not_displayed(self):
        for body in (b'{"to\\u006ben":"DO-NOT-SHOW"}',b'PASSWORD=DO-NOT-SHOW',b'Cookie: DO-NOT-SHOW',b'Bearer DO-NOT-SHOW',b'https://u:DO-NOT-SHOW@host',b'-----BEGIN OPENSSH PRIVATE KEY-----',b'\x00binary',b'A'*40):
            self.sftp.file('apparently-safe.json',body)
            with self.subTest(body_type=body[:4]),self.assertRaises(BrowserError):self.browser.preview(DEFAULT_ROOT,'apparently-safe.json')
        self.sftp.nodes[DEFAULT_ROOT+'/pipe.txt']=attrs(mode=stat.S_IFIFO|0o600)
        with self.assertRaisesRegex(BrowserError,'regular'):self.browser.preview(DEFAULT_ROOT,'pipe.txt')
        self.sftp.file('image.png',b'image')
        with self.assertRaisesRegex(BrowserError,'formats'):self.browser.preview(DEFAULT_ROOT,'image.png')

    def test_changed_file_is_not_returned(self):
        self.sftp.file('file.txt',b'public content');self.sftp.changed=True
        with self.assertRaisesRegex(BrowserError,'changed'):self.browser.preview(DEFAULT_ROOT,'file.txt')

    def test_roots_cannot_expand_into_secret_or_external_trees(self):
        for root in ('/','/etc/stock-discovery','/opt/stock-discovery/../secrets','/opt/stock-discovery/backups','/opt/stock-discovery/.git'):
            with self.subTest(root=root),self.assertRaises(BrowserError):Config(roots=(root,))

    def test_ssh_includes_reused_but_match_commands_never_evaluated(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);child=base/'included';child.write_text('Host bookmyhost\n  User root\n')
            config=base/'config';config.write_text('Include '+str(child)+'\n')
            self.assertIn('Host bookmyhost',ssh_text(config))
            for directive in ('Match exec "touch NEVER"','Match=exec "touch NEVER"'):
                child.write_text(directive)
                with self.assertRaisesRegex(BrowserError,'Match'):ssh_text(config)
            child.write_text('Include '+str(config))
            with self.assertRaisesRegex(BrowserError,'recursive'):ssh_text(config)

    def test_launcher_enforces_loopback_and_disables_public_file_serving(self):
        args=arguments([])
        for option in ('--server.address=127.0.0.1','--server.enableCORS=true','--server.enableXsrfProtection=true','--server.enableStaticServing=false','--browser.gatherUsageStats=false'):
            self.assertIn(option,args)
        with patch('sys.stderr',io.StringIO()),self.assertRaises(SystemExit):arguments(['--host','0.0.0.0'])




class ConnectionTests(unittest.TestCase):
    def module(self,options=None,failure=None):
        class SSHError(Exception):pass
        class BadKey(SSHError):pass
        class Authentication(SSHError):pass
        calls=[];sftp=FakeSFTP()
        sftp.get_channel=lambda:SimpleNamespace(settimeout=lambda n:calls.append(('timeout',n)))
        sftp.close=lambda:calls.append(('sftp_close',))
        class Client:
            def load_system_host_keys(self):calls.append(('system_keys',))
            def load_host_keys(self,path):calls.append(('user_keys',path))
            def set_missing_host_key_policy(self,policy):calls.append(('policy',type(policy).__name__))
            def connect(self,**kwargs):
                calls.append(('connect',kwargs))
                if failure:raise SSHError('NEVER-SHOW-SECRET')
            def open_sftp(self):calls.append(('open_sftp',));return sftp
            def close(self):calls.append(('close',))
        class RejectPolicy:pass
        config=SimpleNamespace(from_text=lambda text:SimpleNamespace(lookup=lambda host:options or {'hostname':'fixture.invalid','user':'fixture','port':'2222','identityfile':['/fixture/key'],'identitiesonly':'yes'}))
        return SimpleNamespace(SSHClient=Client,SSHConfig=config,RejectPolicy=RejectPolicy,
            SSHException=SSHError,BadHostKeyException=BadKey,AuthenticationException=Authentication),calls

    def test_reuses_config_and_host_trust_with_sftp_only(self):
        from stk100_sftp import connect
        module,calls=self.module()
        with tempfile.TemporaryDirectory() as tmp:
            config=Path(tmp)/'config';config.write_text('Host fixture\n')
            known=Path(tmp)/'known';known.write_text('synthetic')
            with patch.dict('sys.modules',{'paramiko':module}):
                with connect(Config(ssh_config=config,known_hosts=known)) as browser:
                    self.assertEqual(browser.listing(DEFAULT_ROOT),([],False))
        options=next(c[1] for c in calls if c[0]=='connect')
        self.assertEqual(options['hostname'],'fixture.invalid');self.assertEqual(options['port'],2222)
        self.assertFalse(options['allow_agent']);self.assertFalse(options['look_for_keys'])
        self.assertIn(('policy','RejectPolicy'),calls)
        self.assertEqual(calls[-2:],[('sftp_close',),('close',)])

    def test_proxy_commands_never_run_and_errors_are_sanitized(self):
        from stk100_sftp import connect
        for options in ({'proxycommand':'touch NEVER'},{'proxyjump':'host'}):
            module,calls=self.module(options)
            with patch.dict('sys.modules',{'paramiko':module}),patch('stk100_sftp.ssh_text',return_value=''):
                with self.assertRaisesRegex(BrowserError,'direct SSH'):
                    with connect(Config()):pass
            self.assertFalse(any(c[0]=='connect' for c in calls))
        module,calls=self.module(failure=True)
        with patch.dict('sys.modules',{'paramiko':module}),patch('stk100_sftp.ssh_text',return_value=''):
            with self.assertRaisesRegex(BrowserError,'SSH/SFTP unavailable') as result:
                with connect(Config()):pass
        self.assertNotIn('NEVER',str(result.exception));self.assertEqual(calls[-1],('close',))

    def test_json_expansion_keeps_rendered_line_limit(self):
        sftp=FakeSFTP();sftp.file('rows.json',b'['+b'{"number":1},'*1000+b'{}]')
        result=ReadOnlyBrowser(sftp,(DEFAULT_ROOT,)).preview(DEFAULT_ROOT,'rows.json')
        self.assertTrue(result['truncated']);self.assertLessEqual(len(result['text'].splitlines()),MAX_LINES)


if __name__=='__main__':unittest.main()
