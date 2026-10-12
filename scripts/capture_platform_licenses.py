"""Capture exact runtime licence evidence without installing or changing packages.
Evidence is not a native-source/conveyance clearance. No container env is collected.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = shlex.split(os.getenv("STK_COMPOSE_COMMAND", "docker compose"))


def run(args):
    return subprocess.check_output(args, text=True)


def capture(expected):
    code = r'''import hashlib,importlib.metadata as md,json,platform,pathlib,subprocess
packages=[]
for d in md.distributions():
 notices={}; native=[]
 for f in d.files or []:
  p=d.locate_file(f)
  if not p.is_file(): continue
  name=p.name.lower()
  if name.startswith(('license','licence','copying','notice')):
   notices[str(f)]=p.read_text(errors='replace')
  if '.so' in name:
   native.append({'path':str(f),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 packages.append({'name':d.metadata['Name'],'version':d.version,'license':d.metadata.get('License-Expression') or d.metadata.get('License'),'classifiers':d.metadata.get_all('Classifier',[]),'sources':d.metadata.get_all('Project-URL',[]),'notices':notices,'native_objects':native})
os_packages=[]
for row in subprocess.check_output(['dpkg-query','-W','-f','${Package}\t${Version}\n'],text=True).splitlines():
 name,version=row.split('\t'); path=pathlib.Path('/usr/share/doc')/name/'copyright'
 os_packages.append({'name':name,'version':version,'copyright':path.read_text(errors='replace') if path.exists() else None})
import psycopg.pq
print(json.dumps({'architecture':platform.machine(),'python':platform.python_version(),'libpq_version':psycopg.pq.version(),'packages':sorted(packages,key=lambda p:p['name']),'os_packages':os_packages}))
'''
    data = json.loads(run([*COMPOSE, "exec", "-T", "api", "python", "-c", code]))
    if data["architecture"] != expected:
        raise ValueError("Captured architecture does not match requested target")
    result = {"architecture": expected, "python_runtime": data, "images": {}, "alpine": {},
              "clearance": "PARTIAL: native component sources/notices and host closure require review"}
    for service in ("api", "worker", "database", "web"):
        container = run([*COMPOSE, "ps", "-q", service]).strip()
        image = run(["docker", "inspect", "--format", "{{.Image}}", container]).strip()
        result["images"][service] = {"id": image, "platform": run(["docker", "image", "inspect", "--format", "{{.Os}}/{{.Architecture}}", image]).strip()}
    for service in ("database", "web"):
        result["alpine"][service] = run([*COMPOSE, "exec", "-T", service, "cat", "/lib/apk/db/installed"])
    result["inputs"] = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
                        ("backend/requirements.txt", "frontend/package-lock.json", "backend/Dockerfile",
                         "worker/Dockerfile", "frontend/Dockerfile", "compose.yaml", "deploy/compose.private.yaml")}
    result["commit"] = run(["git", "rev-parse", "HEAD"]).strip()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--architecture", default="x86_64")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result = capture(args.architecture)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("Captured", result["architecture"], "runtime inventory; clearance remains PARTIAL")
