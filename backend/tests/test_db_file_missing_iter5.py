# STK-079: missing DATABASE_URL_FILE -> 503 with clear detail; recovery -> 200
import os
import pytest
import requests

BASE = os.environ.get('SD_API', 'http://127.0.0.1:8000')
KEY = 'sim-owner-key-synthetic-local-only-000000'
DETAIL = 'Database connection file not found: check DATABASE_URL_FILE points to an existing file.'
MODE = os.environ.get('SD_MODE', 'missing')  # 'missing' or 'recovered'
PATHS = ['/v1/real-research/coverage', '/v1/real-research/scan',
         '/v1/real-research/companies/NSE%3AINE009A01021', '/api/v1/dashboard']


@pytest.fixture(scope='module')
def s():
    s = requests.Session()
    r = s.post(BASE + '/api/v1/session', json={'token': KEY})
    assert r.status_code in (200, 204), r.text
    return s


@pytest.mark.parametrize('path', PATHS)
def test_endpoints(s, path):
    r = s.get(BASE + path)
    print(path, r.status_code, r.text[:200])
    if MODE == 'missing':
        assert r.status_code == 503
        assert r.json()['detail'] == DETAIL
    else:
        assert r.status_code == 200


def test_status(s):
    r = s.get(BASE + '/v1/real-research/status')
    assert r.status_code == 200
    d = r.json()
    print(d.get('database'), d.get('blockers'))
    if MODE == 'missing':
        assert d['database']['state'] == 'unavailable'
        assert d['blockers'][0].startswith('Database is not reachable')
    else:
        assert d['database']['state'] != 'unavailable'
        assert not any(b.startswith('Database is not reachable') for b in d['blockers'])


def test_unauth_still_401():
    r = requests.get(BASE + '/v1/real-research/coverage')
    assert r.status_code == 401
