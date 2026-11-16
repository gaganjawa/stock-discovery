# STK-100 · D3-12 Private operational pilot — local VPS file browser

Small Streamlit operator app using **SFTP only**. It reuses the existing BookMyHost
SSH key and known-host trust; it does not install anything or run commands on the
VPS. No uploads, downloads, edits, deletion, remote shell, public listener or service.
PR #59 and production services are independent of this tool.

## Install once, then launch

From the repository root, using the existing `uv` tool:

```sh
uv venv .venv-vps-browser --python 3.12
uv pip sync --python .venv-vps-browser/bin/python --require-hashes tools/vps_browser/requirements.txt
```

One launch command:

```sh
.venv-vps-browser/bin/python scripts/stk100_browser.py
```

Open **http://127.0.0.1:8502** and click **Connect / Refresh**. Stop with Ctrl-C.
Optional `--port 8512` changes only the local port; a public bind address is not an
option. The launcher overrides global Streamlit bind/CORS/XSRF/static-file/agent
API/upload/telemetry settings. The app also refuses to connect unless the configured
bind address is exactly 127.0.0.1. It is an owner-operated local tool: do not proxy,
forward or expose its port. There is no new credential or application login.

The isolated dependencies are Streamlit and Paramiko (plus hash-locked transitives).
Neither is installed in the existing project runtime, and neither is added to the
production backend requirements or images. The repository's Python/unittest tooling
is reused. Do not use the unrelated untracked root `pyproject.toml` for this tool.

## Existing SSH access and allowlist

Defaults use the verified existing host `160.22.109.189`, user `root`, port 22,
`~/.ssh/stock-discovery-vps`, `~/.ssh/config` and `~/.ssh/known_hosts`. No key is
printed, copied, replaced or enrolled. Host-key mismatch/unknown host fails closed.
HostName, User, Port, IdentityFile and IdentitiesOnly from an existing Host entry
are honored; bounded Include files are supported. `STK100_SSH_HOST` can select an
existing direct Host alias. Match, proxy/command and host-key alias configurations
are intentionally unsupported; the app never invokes SSH commands or ProxyCommand.
Only SFTP stat/canonicalization/list/open-read/seek/read operations are used.

Default allowlist: **`/opt/stock-discovery/deploy/chartink`**. Optional `STK100_ROOTS`
is a colon-separated list of up to eight owner-reviewed project directories, all
under `/opt/stock-discovery`. Roots are read from the local environment, never a
browser text box. `/etc/stock-discovery`, home/SSH directories, databases, volumes,
backups, artifacts and private/secret paths cannot be selected. No VPS path is created.

Breadcrumb buttons navigate within a selected root. Entries show byte size,
permissions and UTC modification time. Refresh opens a fresh short-lived SFTP
session; Disconnect clears the selected preview. No connection opens on initial
page load; session state is local to each browser session, with no cached payloads.

## Read-only boundaries and limits

- Root-owned paths with no group/world write permission only. Every path component
  is checked with lstat, symlinks are rejected (even inside the allowlist), and
  canonical paths must match. Recheck paths and file metadata around reads; changed
  files are withheld. Only regular files are previewed; no devices/FIFOs/sockets.
- This is client-side policy over existing SSH access, not a newly restricted server
  account. SFTP v3 has no atomic `openat/O_NOFOLLOW` primitive. Trusted root-owned
  project directories are therefore required; this tool does not defend against a
  malicious privileged server swapping paths between protocol operations. Do not
  add roots managed by untrusted writers.
- Hidden files, environment/key/credential names, private directories, archives and
  database files are omitted. A second content check withholds previews containing
  credential-like assignments, escaped JSON credential keys, private-key markers,
  bearer tokens, capability URLs or opaque token lines. This deliberately has false
  positives; a neutral filename is not permission to reveal detected credentials.
  Only reviewed non-secret project trees belong in the allowlist; no heuristic can
  identify arbitrary credentials embedded in otherwise innocent prose.
- Directory scans inspect at most 201 entries and display at most 200, counting
  excluded entries toward the cap. Large directories can show a partial listing.
  Maximum path depth 32 and length 4,096. Network operations have 8-second timeouts.
- Each preview reads at most **64 KiB**, displays at most **400 lines / 64 KiB**, and
  reports truncation. Logs use a bounded tail. Small complete JSON is pretty-printed;
  malformed/truncated JSON is literal text. Binary/control-byte content is refused.
  File text is rendered as code, never HTML or executable Markdown.
- UI errors are fixed safe messages; no raw SSH exceptions, credential values or
  remote payloads enter logs/error tracebacks. Streamlit agent API, uploads and static
  serving are disabled by the launcher; CORS and XSRF remain enabled.

Implementation references: [Streamlit configuration](https://docs.streamlit.io/develop/api-reference/configuration/config.toml)
and [Paramiko SFTP](https://docs.paramiko.org/en/stable/api/sftp.html).

## Focused verification

```sh
python -m unittest discover -s scripts -p test_stk100_sftp.py
.venv-vps-browser/bin/python -m unittest discover -s tools/vps_browser -p test_app.py
```

Synthetic tests cover path/secret/symlink rejection, unsafe owners/permissions,
listing/byte/line limits, file-change detection, SSH trust/config reuse, forbidden
command configuration, loopback launch, navigation, previews, refresh/disconnect
and sanitized errors. These do not require VPS connectivity. On 16-Nov, real SFTP
metadata-only verification connected to the existing default root and listed two
visible entries; **zero file previews**, writes, remote commands or service changes.
