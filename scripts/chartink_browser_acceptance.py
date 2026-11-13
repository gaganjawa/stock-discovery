"""Optional local real-browser check, called inside the isolated HTTPS test.

Requires installed frontend dependencies and Playwright Chromium. No API mocking.
"""
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import uvicorn


def verify(app, *, script=None):
    root=Path(__file__).resolve().parents[1]
    sock=socket.socket();sock.bind(('127.0.0.1',0));api_port=sock.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(app,access_log=False,log_level='critical'))
    thread=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True)
    thread.start()
    web=None
    old_origin=os.environ.get("APP_ORIGIN")
    try:
        for _ in range(100):
            if server.started:break
            time.sleep(.05)
        assert server.started
        with tempfile.TemporaryDirectory(prefix='stk097-browser-') as temp:
            dest=Path(temp)
            for filename in subprocess.check_output(['git','ls-files','frontend'],cwd=root,text=True).splitlines():
                src=root/filename;target=dest/Path(filename).relative_to('frontend')
                target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,target)
            (dest/'node_modules').symlink_to(root/'frontend/node_modules',target_is_directory=True)
            with socket.socket() as reservation:
                reservation.bind(('127.0.0.1',0));web_port=reservation.getsockname()[1]
            os.environ['APP_ORIGIN']=f'http://127.0.0.1:{web_port}'
            (dest/'vite.config.ts').write_text("import {defineConfig} from 'vite';import react from '@vitejs/plugin-react';export default defineConfig({plugins:[react()],server:{proxy:{'/api':'http://127.0.0.1:%d','/v1':'http://127.0.0.1:%d'}}});"%(api_port,api_port))
            web=subprocess.Popen(['npm','run','dev','--','--host','127.0.0.1','--port',str(web_port),'--strictPort'],cwd=dest,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            import urllib.request
            for _ in range(100):
                try:
                    urllib.request.urlopen(f'http://127.0.0.1:{web_port}',timeout=1);break
                except OSError:time.sleep(.1)
            script=script or """
const {chromium,expect}=require(process.env.STK_PLAYWRIGHT);
(async()=>{const b=await chromium.launch();try{const p=await b.newPage();
await p.goto(process.env.STK_URL+'/#real-research');
await p.getByLabel('Owner access key').fill('o'.repeat(40));
await p.getByRole('button',{name:'Sign in',exact:true}).click();
await p.getByRole('region',{name:'Research workbench',exact:true}).getByRole('button',{name:'Candidates',exact:true}).click();
const c=p.getByRole('region',{name:'Scanner candidates'});
await expect(c).toContainText('SYN097');await expect(c).toContainText('SYNTHETIC FIXTURE');
await expect(c).toContainText('partial unverified');
await c.getByRole('button',{name:'Save SYN097 to watchlist',exact:true}).click();
await expect(c).toContainText('Saved to watchlist');console.log('PASS HTTPS-delivered candidate in actual UI');
}finally{await b.close()}})().catch(e=>{console.error(e);process.exit(1)});
"""
            subprocess.run(['node','-e',script],cwd=root,env={**os.environ,'STK_URL':f'http://127.0.0.1:{web_port}','STK_PLAYWRIGHT':str(root/'frontend/node_modules/@playwright/test')},check=True,timeout=90)
    finally:
        if old_origin is None:os.environ.pop("APP_ORIGIN",None)
        else:os.environ["APP_ORIGIN"]=old_origin
        if web:
            web.terminate();web.wait(timeout=10)
        server.should_exit=True;thread.join(timeout=10);sock.close()
