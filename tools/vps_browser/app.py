"""Local STK-100 Streamlit UI. No remote commands or mutation controls."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import streamlit as st
from stk100_sftp import BrowserError, Config, connect


def main():
    st.set_page_config(page_title='Stock Discovery · VPS files',layout='wide')
    st.title('VPS project files')
    st.caption('Read-only SFTP · local operator session · no uploads, commands or remote edits')
    if st.get_option('server.address')!='127.0.0.1':
        st.error('Use the local launcher: server.address must be 127.0.0.1.')
        return
    try:config=Config.environment()
    except BrowserError as exc:st.error(str(exc));return
    root=st.selectbox('Allowed project directory',config.roots)
    if st.session_state.get('root')!=root:
        st.session_state.update(root=root,path='',selected=None)
    left,right=st.columns(2)
    if left.button('Connect / Refresh',type='primary'):
        st.session_state['connected']=True
    if right.button('Disconnect'):
        st.session_state.update(connected=False,selected=None)
    if not st.session_state.get('connected'):
        st.info('Connect to browse the configured project directory using existing SSH trust and keys.')
        return
    relative=st.session_state.get('path','')
    crumbs=['']+['/'.join(relative.split('/')[:i]) for i in range(1,len(relative.split('/'))+1)] if relative else ['']
    st.caption('Location: '+root+('/'+relative if relative else ''))
    for index,column in enumerate(st.columns(len(crumbs))):
        crumb=crumbs[index]
        if column.button('Project root' if not crumb else crumb.rsplit('/',1)[-1],key='crumb:'+crumb):
            st.session_state.update(path=crumb,selected=None)
            st.rerun()
    try:
        with connect(config) as browser:
            rows,limited=browser.listing(root,relative)
            if limited:st.warning('Directory scan capped at 200 entries. Excluded/private entries count toward this limit.')
            if not rows:st.info('No visible entries. Private files, symlinks and unsupported entries are excluded.')
            st.caption('Modified times are UTC. Previews read at most 64 KiB and display at most 400 lines; logs show the tail.')
            for row in rows:
                name,metadata=st.columns([2,3])
                label=('Open folder: ' if row['directory'] else 'Preview: ')+row['name']
                if name.button(label,key='entry:'+row['name']):
                    child='/'.join(filter(None,(relative,row['name'])))
                    if row['directory']:
                        st.session_state.update(path=child,selected=None)
                    else:st.session_state['selected']=child
                    st.rerun()
                metadata.text(f"{row['size']:,} bytes · {row['modified']} · {row['permissions']}")
            selected=st.session_state.get('selected')
            if selected:
                st.subheader('Preview: '+selected.rsplit('/',1)[-1])
                preview=browser.preview(root,selected)
                if preview['truncated']:st.warning('Preview truncated by byte/line limits; use approved tools outside this app for larger files.')
                st.caption(f"Read {preview['bytes_read']:,} bytes at offset {preview['offset']:,}")
                st.code(preview['text'],language=preview['language'])
    except BrowserError as exc:
        st.error(str(exc))
    except Exception:
        # Never send exception text, SSH config, raw remote bytes or tracebacks to UI.
        st.error('SFTP read failed or access was denied. Refresh, or check the allowlist and existing SSH access.')


if __name__=='__main__':main()
