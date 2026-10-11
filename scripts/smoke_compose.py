"""Smoke-check the running synthetic Compose stack; no external services used."""
import http.client
import json
import os
import subprocess
import shutil
import time
import urllib.error
import urllib.request


def compose(*args):
    command = ['docker-compose'] if shutil.which('docker-compose') else ['docker','compose']
    return subprocess.check_output([*command,*args],text=True)


def read_url(url):
    deadline = time.monotonic() + 90
    while True:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                return response.read().decode()
        except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.RemoteDisconnected):
            if time.monotonic() >= deadline:
                raise
            time.sleep(1)


def main():
    api = 'http://127.0.0.1:' + os.getenv('API_PORT', '8000')
    web = 'http://127.0.0.1:' + os.getenv('WEB_PORT', '5173')
    assert json.loads(read_url(api + '/healthz')) == {'status': 'ok', 'data_mode': 'synthetic'}
    demo = json.loads(read_url(api + '/api/v1/demo/recommendation'))
    assert demo['is_synthetic'] is True and demo['is_actionable'] is False
    html = read_url(web)
    assert '<div id="root"></div>' in html and '/assets/' in html
    import re
    asset = re.search(r'src="(/assets/[^\"]+\.js)"', html).group(1)
    assert len(read_url(web + asset)) > 1000
    assert compose('exec', '-T', 'database', 'sh', '-c',
                   'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT 1"').strip() == '1'
    cycle = json.loads(compose('exec', '-T', 'worker', 'python', '-m', 'worker.main', '--once'))
    assert cycle['recommendation']['is_actionable'] is False
    for service in ('api', 'worker'):
        url = compose('exec', '-T', service, 'printenv', 'DATABASE_URL').strip()
        assert '${' not in url and '@database:5432/' in url
    print('PASS: API, built UI asset, PostgreSQL query, worker cycle and environment interpolation')


if __name__ == '__main__':
    main()
