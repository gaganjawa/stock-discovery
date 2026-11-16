"""STK-100 / D3-12: bounded, read-only SFTP browser policy (no shell API)."""
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import glob
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

CEILING = PurePosixPath('/opt/stock-discovery')
DEFAULT_ROOT = '/opt/stock-discovery/deploy/chartink'
MAX_ENTRIES = 200
MAX_BYTES = 65536
MAX_LINES = 400
TIMEOUT = 8
SECRET_NAME = re.compile(r'(secret|credential|password|passwd|token|private|backup|dump|database|wallet|api.?key|access.?key|cookie|session|auth|id_rsa|id_ed25519)', re.I)
DENIED_NAMES = {'env','environment','owner_url','receiver_url','worker_url','db_url','db_password','webhook','pull','inbox','volumes','data','artifacts'}
TEXT_SUFFIXES = {'.txt','.md','.json','.log','.yaml','.yml','.toml','.ini','.conf','.py','.ts','.tsx','.js','.css','.html','.sh'}
SECRET_CONTENT = re.compile(
    r'-----BEGIN [^-]*(?:PRIVATE KEY|OPENSSH)|'
    r'\b(?:Bearer|Basic)\s+[A-Za-z0-9+/_.=-]+|'
    r'(?:password|passwd|secret|token|credential|api[_-]?key|access[_-]?key(?:[_-]?id)?|cookie|authorization|webhook_url)\b["\x27]?\s*[:=]|'
    r'[a-z][a-z0-9+.-]*://[^\s/]+:[^\s/]+@|/hooks/chartink/[^\s"\x27]+|'
    r'\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+|(?m:^\s*[A-Za-z0-9+/=_-]{32,}\s*$)', re.I)


class BrowserError(ValueError):
    """Only fixed, non-secret messages are presented by the UI."""


def permitted_name(name):
    return (bool(name) and name not in ('.','..') and not name.startswith('.')
            and '/' not in name and '\\' not in name and all(32 <= ord(c) < 127 for c in name)
            and len(name) <= 160 and not SECRET_NAME.search(name)
            and name.lower() not in DENIED_NAMES
            and not any(part in ('env','pem','key','p12','pfx','bak','sqlite','db','sql','gz','zip','tar') for part in name.lower().split('.')))


@dataclass(frozen=True)
class Config:
    host: str = '160.22.109.189'
    roots: tuple[str,...] = (DEFAULT_ROOT,)
    ssh_config: Path = Path.home()/'.ssh/config'
    known_hosts: Path = Path.home()/'.ssh/known_hosts'
    default_key: Path = Path.home()/'.ssh/stock-discovery-vps'

    def __post_init__(self):
        if not self.host or any(c.isspace() for c in self.host):raise BrowserError('Invalid SSH host or alias.')
        if not 1 <= len(self.roots) <= 8:raise BrowserError('Configure between one and eight project roots.')
        for root in self.roots:
            path=PurePosixPath(root)
            if str(path)!=root or not path.is_relative_to(CEILING) or '..' in path.parts:
                raise BrowserError('Roots must be canonical absolute paths under /opt/stock-discovery.')
            if any(not permitted_name(part) for part in path.relative_to(CEILING).parts):
                raise BrowserError('A configured root contains an excluded private directory.')

    @classmethod
    def environment(cls):
        roots=tuple(os.getenv('STK100_ROOTS',DEFAULT_ROOT).split(':'))
        return cls(host=os.getenv('STK100_SSH_HOST','160.22.109.189'),roots=roots)


def ssh_text(path, *, depth=0, seen=None):
    """Expand bounded OpenSSH Includes without invoking ssh or Match exec."""
    seen=set() if seen is None else seen
    path=Path(path).expanduser().resolve()
    if depth>4 or path in seen or len(seen)>=16:raise BrowserError('SSH config includes are recursive or exceed limits.')
    if not path.is_file():return ''
    seen.add(path)
    with path.open('rb') as source:data=source.read(MAX_BYTES+1)
    if len(data)>MAX_BYTES:raise BrowserError('SSH config exceeds the local size limit.')
    output=[]
    import shlex
    for line in data.decode('utf-8').splitlines():
        words=shlex.split(re.sub(r'^(\s*[^\s=]+)\s*=\s*',r'\1 ',line),comments=True)
        if not words:continue
        directive=words[0].lower()
        if directive=='match':raise BrowserError('SSH Match directives are unsupported; use a direct Host entry without commands.')
        if directive=='include':
            for pattern in words[1:]:
                target=Path(pattern).expanduser()
                if not target.is_absolute():target=Path.home()/'.ssh'/target
                for included in sorted(glob.glob(str(target))):
                    output.append(ssh_text(included,depth=depth+1,seen=seen))
        else:output.append(line)
    return '\n'.join(output)+'\n'


@contextmanager
def connect(config):
    import paramiko
    client=paramiko.SSHClient()
    sftp=None
    try:
        parsed=paramiko.SSHConfig.from_text(ssh_text(config.ssh_config))
        options=parsed.lookup(config.host)
        if any(options.get(k) for k in ('proxycommand','proxyjump','localcommand','remotecommand','hostkeyalias')):
            raise BrowserError('Use a direct SSH Host entry without proxy, command or host-key aliases.')
        # Never accept new host keys or write known_hosts. Existing SSH trust is reused.
        client.load_system_host_keys()
        if config.known_hosts.is_file():client.load_host_keys(str(config.known_hosts))
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
        keys=options.get('identityfile') or [str(config.default_key)]
        client.connect(hostname=options.get('hostname',config.host),
            username=options.get('user','root'),port=int(options.get('port','22')),
            key_filename=[str(Path(key).expanduser()) for key in keys],
            allow_agent=options.get('identitiesonly','no').lower()!='yes',look_for_keys=False,
            timeout=TIMEOUT,banner_timeout=TIMEOUT,auth_timeout=TIMEOUT,channel_timeout=TIMEOUT)
        sftp=client.open_sftp()
        sftp.get_channel().settimeout(TIMEOUT)
        yield ReadOnlyBrowser(sftp,config.roots)
    except BrowserError:raise
    except paramiko.BadHostKeyException:
        raise BrowserError('SSH host key changed. Verify it outside this app; no key was accepted.') from None
    except paramiko.AuthenticationException:
        raise BrowserError('SSH authentication failed. Check the existing key or unlocked SSH agent.') from None
    except (paramiko.SSHException,OSError,ValueError):
        raise BrowserError('SSH/SFTP unavailable. Check network, known_hosts, key access and direct SSH configuration.') from None
    finally:
        if sftp is not None:sftp.close()
        client.close()


class ReadOnlyBrowser:
    def __init__(self,sftp,roots):
        Config(roots=tuple(roots))
        self._sftp=sftp
        self.roots=tuple(roots)

    def _path(self,root,relative=''):
        if root not in self.roots:raise BrowserError('Directory is outside the configured allowlist.')
        if relative and (relative.startswith('/') or any(not permitted_name(p) for p in relative.split('/'))):
            raise BrowserError('Path is excluded by the read-only policy.')
        path=PurePosixPath(root)/relative
        if len(str(path))>4096 or len(path.parts)>32:raise BrowserError('Path exceeds the navigation depth/length limit.')
        # Reject symlinks at every component, including the root and its ancestors.
        cursor=PurePosixPath('/')
        for part in path.parts[1:]:
            cursor/=part
            info=self._sftp.lstat(str(cursor))
            if stat.S_ISLNK(info.st_mode):raise BrowserError('Symlinks are excluded.')
            if info.st_uid!=0 or info.st_mode & 0o022:
                raise BrowserError('Only root-owned paths without group/world write access are allowed.')
        if self._sftp.normalize(str(path))!=str(path):raise BrowserError('Canonical path escaped the allowlist.')
        return str(path),info

    def listing(self,root,relative=''):
        path,info=self._path(root,relative)
        if not stat.S_ISDIR(info.st_mode):raise BrowserError('Selected path is not a directory.')
        rows=[];limited=False
        iterator=self._sftp.listdir_iter(path,read_aheads=1)
        try:
            for index,item in enumerate(iterator):
                if index>=MAX_ENTRIES:limited=True;break
                if not permitted_name(item.filename) or stat.S_ISLNK(item.st_mode):continue
                if not (stat.S_ISDIR(item.st_mode) or stat.S_ISREG(item.st_mode)):continue
                if item.st_uid!=0 or item.st_mode & 0o022:continue
                rows.append(dict(name=item.filename,directory=stat.S_ISDIR(item.st_mode),
                    size=item.st_size,modified=datetime.fromtimestamp(item.st_mtime,timezone.utc).isoformat(),
                    permissions=stat.filemode(item.st_mode)))
        finally:iterator.close()
        self._path(root,relative)  # Recheck after listing; do not show a switched path.
        return sorted(rows,key=lambda r:(not r['directory'],r['name'].lower())),limited

    def preview(self,root,relative):
        path,before=self._path(root,relative)
        name=PurePosixPath(path).name
        if not stat.S_ISREG(before.st_mode):raise BrowserError('Only regular text files can be previewed.')
        suffix=PurePosixPath(path).suffix.lower()
        if suffix not in TEXT_SUFFIXES and name not in ('Caddyfile','Dockerfile','Makefile','LICENSE'):
            raise BrowserError('Preview is limited to approved text, JSON and log formats.')
        with self._sftp.open(path,'rb') as source:
            opened=source.stat()
            signature=lambda s:(s.st_mode,s.st_size,s.st_mtime,s.st_uid,s.st_gid)
            if signature(before)!=signature(opened):raise BrowserError('File changed during access. Refresh and retry.')
            self._path(root,relative)
            start=max(0,opened.st_size-MAX_BYTES) if suffix=='.log' else 0
            if start:source.seek(start)
            data=source.read(MAX_BYTES)
            after=source.stat()
            _,current=self._path(root,relative)
            if signature(opened)!=signature(after) or signature(after)!=signature(current):
                raise BrowserError('File changed during preview. Refresh and retry.')
        if b'\x00' in data or any(b<9 or 13<b<32 for b in data):raise BrowserError('Binary/control-byte content is not previewed.')
        text=data.decode('utf-8',errors='replace')
        hidden=bool(SECRET_CONTENT.search(text))
        # JSON may spell credential keys with Unicode escapes; inspect decoded keys
        # before rendering or pretty-printing, including bounded JSON/log prefixes.
        for token in re.finditer(r'"(?:[^"\\]|\\.)*"\s*:',text):
            try:key=json.loads(token.group().rstrip()[:-1].rstrip())
            except ValueError:continue
            hidden=hidden or bool(SECRET_NAME.search(key)) or key.lower() in ('webhook_url','api_key','authorization')
        if hidden:raise BrowserError('Preview hidden: possible credentials or capability URL detected.')
        lines=text.splitlines()
        clipped=bool(start or opened.st_size>len(data) or len(lines)>MAX_LINES)
        if start and lines:lines=lines[1:]
        text='\n'.join(lines[-MAX_LINES:] if suffix=='.log' else lines[:MAX_LINES])
        if suffix=='.json' and not clipped:
            try:text=json.dumps(json.loads(text),indent=2,ensure_ascii=True)
            except (ValueError,RecursionError):pass  # Show bounded literal text, never evaluate it.
        # Pretty JSON can expand; cap the final rendered form as well.
        rendered=text.splitlines()
        if len(rendered)>MAX_LINES:text='\n'.join(rendered[:MAX_LINES]);clipped=True
        encoded=text.encode('utf-8')
        if len(encoded)>MAX_BYTES:text=encoded[:MAX_BYTES].decode('utf-8',errors='ignore');clipped=True
        return dict(text=text,truncated=clipped,bytes_read=len(data),offset=start,
                    language='json' if suffix=='.json' else 'text')
