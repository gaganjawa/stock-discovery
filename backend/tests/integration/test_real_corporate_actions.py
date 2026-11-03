"""STK-079: corporate actions on a disposable database; payloads and grants are fabricated."""
import json
import psycopg
import pytest
from test_rag_research import isolated_url
from test_real_market import grant, NOW
from worker.real_market import MarketConfig, ingest_configured_actions
from worker.providers.upstox import observed_revision, RevisionPages
from stock_discovery_analysis.real_views import company, ViewConfig
from stock_discovery_analysis.real_access import SourceConfig
from stock_discovery_analysis.revisions import InstrumentData
from stock_discovery_analysis.revision_storage import Stream, ingest_next
from stock_discovery_contracts.rights import UseRequest

LISTING = 'NSE:INE009A01021'


def payload(final='5.5'):
    return {'status': 'success', 'data': [
        {'name': 'Dividend', 'expiry_date': '14 Aug 2026', 'amount': final, 'ratio': None,
         'event_details': [{'name': 'Dividend type', 'value': 'Final'}]},
        {'name': 'Bonus', 'expiry_date': '02 Jul 2018', 'amount': None, 'ratio': '1:1', 'event_details': []}]}


def setup(conn, tmp_path, scopes):
    g = grant().model_copy(update={'scopes': scopes})
    grants = tmp_path / 'grants.json'; grants.write_text(json.dumps([g.model_dump(mode='json')]))
    token = tmp_path / 'token'; token.write_text('test-token-not-real')
    identity = observed_revision(InstrumentData(kind='instrument', issuer_id='INE009A01021', symbol='INFY', isin='INE009A01021',
        series='EQ', status='active', lot_size=1, tick_size='0.05', effective_at='2026-01-01T00:00:00Z'), listing=LISTING, fetched=NOW)
    request = UseRequest(source_id='upstox', account_ref='test', scope='universe', uses=('acquire', 'store'), region='IN',
        destination_region=None, processor_ref=None, requested_at=NOW, synthetic=False, units=100, retention_days=365, attribution_present=True)
    ingest_next(conn, Stream(stream_id='test-universe', source_id='upstox', account_ref='test', scope='universe'),
        RevisionPages((identity,)), load_grant=lambda: g, request=request, audit=lambda d: None, clock=lambda: NOW)
    config = MarketConfig(account_ref='test', grant_file=str(grants), token_file=str(token), retention_days=365, corporate_actions=True)
    view = ViewConfig(sources=SourceConfig(grant_file=str(grants), retention_days=365), listing_ids=(LISTING,))
    return config, view


class Provider:
    responses = []; calls = []
    def __init__(self, **kw): self.access = kw['access']
    def close(self): pass
    def _get(self, url, stream):
        self.access.require(stream, ('acquire',)); Provider.calls.append(url)
        return json.dumps(Provider.responses.pop(0)).encode()


def test_actions_append_corrections_and_are_shown_without_adjustment_arithmetic(isolated_url, tmp_path):
    Provider.calls.clear(); Provider.responses[:] = [payload(), payload(), payload('6')]
    market = {'instruments': [{'listing_id': LISTING}]}
    with psycopg.connect(isolated_url, autocommit=True) as conn:
        config, view = setup(conn, tmp_path, ('prices', 'universe', 'calendar', 'corporate_actions'))
        run = lambda at: ingest_configured_actions(conn, config, market, clock=lambda: at, client_factory=Provider, pause=0)
        first = run(NOW)['listings'][0]
        assert first == dict(listing_id=LISTING, observed=2, stored=2, types={'dividend': 1, 'unsupported': 1}, arithmetic='dividend_cash_only')
        assert Provider.calls == ['https://api.upstox.com/v2/fundamentals/INE009A01021/corporate-actions']
        assert run('2026-10-20T12:00:00Z')['listings'][0]['stored'] == 0
        assert run('2026-10-21T12:00:00Z')['listings'][0]['stored'] == 1
        rows = conn.execute("SELECT sequence,supersedes_id IS NOT NULL FROM discovery.revisions WHERE kind='action' ORDER BY sequence").fetchall()
        assert sorted(rows) == [(1, False), (1, False), (2, True)]
        shown = company(conn, view, LISTING, clock=lambda: '2026-10-22T00:00:00Z')['corporate_actions']
        assert [(a['type'], a['cash_per_share'], a['effective_at']) for a in shown] == [
            ('dividend', '6', '2026-08-13T18:30:00Z'), ('unsupported', None, '2018-07-01T18:30:00Z')]
        # The earlier cutoff sees only what had been observed then.
        assert company(conn, view, LISTING, clock=lambda: '2026-10-22T00:00:00Z', cutoff_at='2026-10-20T13:00:00Z')['corporate_actions'][0]['cash_per_share'] == '5.5'
        assert conn.execute('SELECT count(*) FROM discovery.recommendations').fetchone()[0] == 0


def test_missing_corporate_action_scope_denies_before_any_request(isolated_url, tmp_path):
    Provider.calls.clear(); Provider.responses[:] = [payload()]
    with psycopg.connect(isolated_url, autocommit=True) as conn:
        config, _ = setup(conn, tmp_path, ('prices', 'universe', 'calendar'))
        before = conn.execute("SELECT count(*) FROM discovery.revisions WHERE kind='action'").fetchone()[0]
        with pytest.raises(PermissionError):
            ingest_configured_actions(conn, config, {'instruments': [{'listing_id': LISTING}]}, clock=lambda: NOW, client_factory=Provider, pause=0)
        assert Provider.calls == [] and conn.execute("SELECT count(*) FROM discovery.revisions WHERE kind='action'").fetchone()[0] == before
