from types import SimpleNamespace
import importlib
from fastapi.testclient import TestClient
from app.main import app
from app import real_research as api
from app.research import db


def client(monkeypatch,tmp_path):
    monkeypatch.setenv('AUTH_TOKEN','w'*40)
    monkeypatch.setenv('REAL_WATCHLIST_DIR',str(tmp_path/'private'))
    monkeypatch.setattr(api,'view_config',lambda:SimpleNamespace(listing_ids=['A','B']))
    app.dependency_overrides[db]=lambda:None
    return TestClient(app),{'Authorization':'Bearer '+'w'*40}


def test_private_persistence_isolation_and_validation(monkeypatch,tmp_path):
    c,h=client(monkeypatch,tmp_path)
    try:
        assert c.get('/v1/real-research/watchlist').status_code==401
        assert c.put('/v1/real-research/watchlist/A',json={'note':'secret'}).status_code==401
        assert c.put('/v1/real-research/watchlist/X',headers=h,json={}).status_code==404
        assert c.put('/v1/real-research/watchlist/A',headers=h,json={'note':'x'*2001}).status_code==422
        assert c.put('/v1/real-research/watchlist/A',headers=h,json={'action':'BUY'}).status_code==422
        assert c.put('/v1/real-research/watchlist/A',headers=h,json={'note':'private research','status':'Monitoring','review_date':'2026-11-10'}).status_code==200
        from app import watchlist
        importlib.reload(watchlist)
        assert watchlist.store()['entries']['A']['note']=='private research'
        assert (tmp_path/'private/watchlist.json').stat().st_mode & 0o777==0o600
        assert c.get('/v1/real-research/watchlist',headers=h).headers['cache-control']=='no-store'
        assert c.delete('/v1/real-research/watchlist/A',headers=h).json()['entries']=={}
    finally:app.dependency_overrides.clear()


def test_denied_comparison_has_no_values_or_promoted_rank(monkeypatch,tmp_path):
    c,h=client(monkeypatch,tmp_path)
    from stock_discovery_analysis import real_views,real_scan_view
    monkeypatch.setattr(real_scan_view,'scan_view',lambda *a:dict(scan=None))
    def company(conn,config,listing):
        if listing=='B':raise PermissionError('private denial')
        return dict(symbol='A',price_series=[],adjusted_research=dict(unavailable_reasons=['session_coverage_unavailable']))
    monkeypatch.setattr(real_views,'company',company)
    try:
        r=c.get('/v1/real-research/workbench',headers=h)
        assert r.status_code==200
        d=r.json();assert d['actionable'] is False and d['qualified'] is False
        assert d['rows'][0]['state']=='unavailable'
        assert d['rows'][1]['state']=='denied' and 'detail' not in d['rows'][1]
        assert d['rows'][1]['screening']=={}
        assert 'private denial' not in r.text
    finally:app.dependency_overrides.clear()


def test_cookie_notes_require_same_origin(monkeypatch,tmp_path):
    c,h=client(monkeypatch,tmp_path)
    monkeypatch.setenv('COOKIE_SECURE','false')
    try:
        c.post('/api/v1/session',json={'token':'w'*40})
        assert c.put('/v1/real-research/watchlist/A',json={}).status_code==403
        assert c.put('/v1/real-research/watchlist/A',json={},headers={'Origin':'http://testserver'}).status_code==200
    finally:app.dependency_overrides.clear()


def test_review_marker_survives_note_edits_and_restart(monkeypatch,tmp_path):
    c,h=client(monkeypatch,tmp_path)
    from stock_discovery_analysis import real_views
    monkeypatch.setattr(real_views,'company',lambda *a:dict(price_series=[dict(fetched_at='2026-11-04T12:00:00Z')]))
    try:
        c.put('/v1/real-research/watchlist/A',headers=h,json={'note':'initial'})
        assert c.post('/v1/real-research/watchlist/A/review',headers=h).status_code==200
        c.put('/v1/real-research/watchlist/A',headers=h,json={'note':'changed'})
        fresh=TestClient(app).get('/v1/real-research/watchlist',headers=h).json()['entries']['A']
        assert fresh['reviewed_observation']=='2026-11-04T12:00:00Z' and fresh['note']=='changed'
        def deny(*a):raise PermissionError()
        monkeypatch.setattr(real_views,'company',deny)
        monkeypatch.setattr(api,'schema_state',lambda:dict(state='current'))
        assert c.post('/v1/real-research/watchlist/A/review',headers=h).status_code==403
    finally:app.dependency_overrides.clear()
