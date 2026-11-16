"""Optional Streamlit AppTest acceptance; mock SFTP only, no remote connection."""
from contextlib import contextmanager
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from streamlit import config
from streamlit.testing.v1 import AppTest
from stk100_sftp import BrowserError,DEFAULT_ROOT


class Browser:
    def listing(self,root,relative):
        if relative:return [dict(name='state.json',directory=False,size=20,modified='2026-11-16T00:00:00+00:00',permissions='-rw-r--r--')],False
        return [dict(name='logs',directory=True,size=0,modified='2026-11-16T00:00:00+00:00',permissions='drwxr-xr-x')],False
    def preview(self,root,relative):
        assert relative=='logs/state.json'
        return dict(text='{"status":"synthetic"}',language='json',truncated=False,bytes_read=22,offset=0)


class AppTests(unittest.TestCase):
    def setUp(self):
        self.original=config.get_option('server.address');config.set_option('server.address','127.0.0.1')
        self.addCleanup(config.set_option,'server.address',self.original)
    def app(self):return AppTest.from_file(str(Path(__file__).with_name('app.py')),default_timeout=10)
    def button(self,app,label):return next(b for b in app.button if b.label==label)
    def test_connect_breadcrumb_preview_refresh_disconnect(self):
        calls=[]
        @contextmanager
        def connection(cfg):calls.append(cfg);yield Browser()
        with patch('stk100_sftp.connect',connection):
            app=self.app().run()
            self.assertFalse(app.exception);self.assertEqual(calls,[])
            self.button(app,'Connect / Refresh').click().run()
            self.button(app,'Open folder: logs').click().run()
            self.assertIn(DEFAULT_ROOT+'/logs',[c.value.removeprefix('Location: ') for c in app.caption])
            self.button(app,'Preview: state.json').click().run()
            self.assertEqual(app.code[0].value,'{"status":"synthetic"}')
            before=len(calls);self.button(app,'Connect / Refresh').click().run();self.assertGreater(len(calls),before)
            self.button(app,'Project root').click().run();self.assertFalse(app.code)
            self.button(app,'Disconnect').click().run();self.assertFalse(app.code)
            self.assertFalse(app.exception)
    def test_connection_errors_are_visible_without_exception_values(self):
        @contextmanager
        def connection(cfg):raise OSError('PRIVATE-TOKEN');yield
        with patch('stk100_sftp.connect',connection):
            app=self.app().run();self.button(app,'Connect / Refresh').click().run()
            self.assertFalse(app.exception)
            self.assertIn('SFTP read failed',app.error[0].value)
            self.assertNotIn('PRIVATE',app.error[0].value)
    def test_public_binding_refuses_connection(self):
        config.set_option('server.address','0.0.0.0')
        with patch('stk100_sftp.connect') as connect:
            app=self.app().run();self.assertIn('127.0.0.1',app.error[0].value);connect.assert_not_called()


if __name__=='__main__':unittest.main()
