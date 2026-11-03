"""Synthetic SDK/master contracts only; never genuine Breeze market evidence."""
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from stock_discovery_analysis.evidence_storage import Access
from stock_discovery_analysis.revision_storage import Stream
from stock_discovery_contracts.rights import Grant, UseRequest
from worker.providers.breeze_probe import SOURCE, ISIN, probe_infy, resolve_infy

NOW = '2026-11-02T12:00:00Z'
MASTER = ('Token, "ShortName", "Series", "CompanyName", "ISINCode", "ExchangeCode"\n'
          '123,"INFTEC","EQ","Fabricated test company",'+ISIN+',INFY\n')
U = Stream(stream_id='TEST-BREEZE-U', source_id=SOURCE, account_ref='test-only', scope='universe')
P = U.model_copy(update={'stream_id': 'TEST-BREEZE-P', 'scope': 'prices'})


def fixture(count=30):
    grant = Grant(schema_version='1.0.0', grant_id='TEST ONLY NOT PERMISSION', version='1',
        source_id=SOURCE, account_ref='test-only', status='active', synthetic=False,
        approval_evidence_ref='FABRICATED TEST ONLY', valid_from_at='2026-01-01T00:00:00Z',
        expires_at='2027-01-01T00:00:00Z', revoked_at=None,
        allowed_uses=('acquire', 'derive'), scopes=('universe', 'prices'), regions=('IN',),
        external_processors=(), retention_days=1, deletion_deadline_days=0,
        attribution='TEST ONLY', max_units_per_operation=100, audit_tombstones_permitted=False)
    def request(s):
        return UseRequest(source_id=s.source_id, account_ref=s.account_ref, scope=s.scope,
            uses=('acquire',), region='IN', destination_region=None, processor_ref=None,
            requested_at=NOW, synthetic=False, units=100, retention_days=1, attribution_present=True)
    access = Access(lambda s: grant, request, lambda _: None, lambda: NOW)
    # Calendar labels below are fictional, not assertions of actual NSE sessions.
    rows = [dict(stock_code='INFTEC', exchange_code='NSE', product_type=None,
                 datetime=(date(2026, 9, 1)+timedelta(days=i)).isoformat()+' 00:00:00',
                 open='10', high='12', low='9', close='11', volume='100') for i in range(count)]
    response = dict(Status=200, Error=None, Success=rows)
    calls = []
    def names(**kw):
        calls.append(('get_names', kw))
        return dict(exchange_code='NSE', exchange_stock_code='INFY', isec_stock_code='INFTEC')
    def history(**kw):
        calls.append(('get_historical_data_v2', kw))
        return response
    sdk = SimpleNamespace(get_names=names, get_historical_data_v2=history)
    def run(**kw):
        return probe_infy(sdk, access=access, universe=U, prices=P, master_csv=MASTER,
                          start=kw.pop('start', '2026-09-01'), end=kw.pop('end', '2026-10-30'), **kw)
    return sdk, access, response, calls, run


def test_official_quoted_header_shape_resolves_isin_not_nse_symbol():
    assert resolve_infy(MASTER) == 'INFTEC'


@pytest.mark.parametrize('master', [
    MASTER.replace(ISIN, 'IN0000000000'), MASTER.replace('INFY', 'OTHER'),
    MASTER.replace('"EQ"', '"BE"'), MASTER.splitlines()[0]+'\n',
    MASTER+MASTER.splitlines()[1]+'\n', MASTER.replace('"ISINCode"', '"WrongColumn"'),
    MASTER.replace('"INFTEC"', '""')])
def test_missing_conflicting_or_ambiguous_identity_denies(master):
    with pytest.raises(ValueError, match='breeze_'):
        resolve_infy(master)


def test_only_two_read_methods_and_correct_cash_daily_provider_code():
    sdk, access, response, calls, run = fixture()
    result = run()
    assert calls == [('get_names', dict(exchange_code='NSE', stock_code='INFY')),
                     ('get_historical_data_v2', dict(interval='1day',
                        from_date='2026-09-01T00:00:00.000Z', to_date='2026-10-30T23:59:59.000Z',
                        stock_code='INFTEC', exchange_code='NSE', product_type='cash'))]
    assert result['provider_status'] == 200 and result['provider_error'] is None
    assert result['minimum_30_date_labels'] and result['row_count'] == 30
    assert result['status'] == 'INSUFFICIENT_EVIDENCE'
    assert result['price_basis'] == result['volume_basis'] == 'unknown'
    assert result['published_at'] is result['first_available_at'] is None
    assert result['session_coverage'] == 'unverified'
    assert not result['ohlcv_values_validated'] and not result['corporate_actions_verified']
    assert not any(result[k] for k in ('actionable', 'publication_authorized',
        'paper_admission_authorized', 'storage_activated', 'immutable_revisions_persisted'))
    assert 'Success' not in result and 'open' not in str(result)


@pytest.mark.parametrize('count', [0, 29, 30])
def test_empty_and_insufficient_samples_never_gain_qualification(count):
    result = fixture(count)[-1]()
    assert result['minimum_30_date_labels'] == (count >= 30)
    assert result['status'] == 'INSUFFICIENT_EVIDENCE'


@pytest.mark.parametrize('status,code', [(401, 'authentication'), (403, 'authorization')])
def test_rejected_session_is_sanitized_without_retry_or_login(status, code):
    sdk, _, response, calls, run = fixture()
    response.update(Status=status, Error='PRIVATE BODY MUST NOT LEAK')
    with pytest.raises(PermissionError, match='breeze_'+code+'_rejected') as e:
        run()
    assert 'PRIVATE' not in str(e.value) and len(calls) == 2


def test_sdk_exception_is_sanitized():
    sdk, _, _, calls, run = fixture()
    def fail(**kw):
        raise RuntimeError('PRIVATE SESSION URL MUST NOT LEAK')
    sdk.get_names = fail
    with pytest.raises(RuntimeError, match='^breeze_sdk_read_failed$') as e:
        run()
    assert e.value.__suppress_context__ and not calls


def test_grant_or_fence_denial_precedes_sdk_reads():
    sdk, access, _, calls, run = fixture()
    object.__setattr__(access, 'load_grant', lambda s: None)
    with pytest.raises(PermissionError):
        run()
    assert not calls


def test_existing_fence_denial_is_not_bypassed():
    sdk, _, _, calls, _ = fixture()
    def denied(*_):
        raise PermissionError('grant_fenced')
    with pytest.raises(PermissionError, match='grant_fenced'):
        probe_infy(sdk, access=SimpleNamespace(require=denied), universe=U, prices=P,
                   master_csv=MASTER, start='2026-09-01', end='2026-10-30')
    assert not calls


@pytest.mark.parametrize('status', [401, 403])
def test_names_rejection_also_preserves_typed_sanitized_classification(status):
    sdk, _, _, calls, run = fixture()
    sdk.get_names = lambda **_: dict(Status=status, Error='PRIVATE BODY')
    with pytest.raises(PermissionError, match='breeze_.*_rejected'):
        run()
    assert not calls


def test_universe_revocation_during_prices_rejects_final_result():
    sdk, access, response, calls, run = fixture()
    original = sdk.get_historical_data_v2
    def revoke(**kw):
        result = original(**kw)
        object.__setattr__(access, 'load_grant', lambda s: None if s.scope == 'universe' else grant)
        return result
    grant = access.load_grant(P)
    sdk.get_historical_data_v2 = revoke
    with pytest.raises(PermissionError):
        run()
    assert len(calls) == 2


def test_sdk_mapping_cannot_override_master_isin():
    sdk, _, _, calls, run = fixture()
    sdk.get_names = lambda **_: dict(exchange_code='NSE', exchange_stock_code='INFY', isec_stock_code='OTHER')
    with pytest.raises(ValueError, match='breeze_sdk_identity_mismatch'):
        run()
    assert not calls


@pytest.mark.parametrize('field,value', [('stock_code', 'INFY'), ('exchange_code', 'NFO'),
    ('product_type', 'futures'), ('datetime', '2026-12-01 00:00:00'), ('datetime', 'bad')])
def test_foreign_or_future_rows_fail_closed(field, value):
    _, _, response, _, run = fixture()
    response['Success'][0][field] = value
    with pytest.raises(ValueError, match='breeze_'):
        run()


def test_duplicate_dates_do_not_inflate_history():
    _, _, response, _, run = fixture()
    response['Success'][1]['datetime'] = response['Success'][0]['datetime']
    with pytest.raises(ValueError, match='breeze_duplicate'):
        run()


def test_oversized_response_is_rejected_before_traversal():
    _, _, response, _, run = fixture()
    response['Success'] = [{}]*92
    with pytest.raises(ValueError, match='breeze_response_limit'):
        run()


@pytest.mark.parametrize('changes', [dict(source_id='other'), dict(account_ref='other'), dict(scope='news')])
def test_source_account_and_scope_mismatch_never_reaches_sdk(changes):
    sdk, access, _, calls, _ = fixture()
    with pytest.raises(ValueError, match='breeze_stream_mismatch'):
        probe_infy(sdk, access=access, universe=U, prices=P.model_copy(update=changes),
                   master_csv=MASTER, start='2026-09-01', end='2026-10-30')
    assert not calls


@pytest.mark.parametrize('status,error', [(True, None), ('200', None), (200, 'private upstream error')])
def test_original_status_must_be_success_without_error(status, error):
    _, _, response, _, run = fixture()
    response.update(Status=status, Error=error)
    with pytest.raises(ValueError, match='^breeze_provider_failed$'):
        run()


def test_missing_original_error_metadata_is_not_invented_as_null():
    _, _, response, _, run = fixture()
    del response['Error']
    with pytest.raises(ValueError, match='breeze_provider_failed'):
        run()


@pytest.mark.parametrize('start,end', [('2026-10-30', '2026-09-01'), ('2026-01-01', '2026-10-30'),
    ('invalid', '2026-10-30'), ('2026-09-01', '2026-11-02'), ('20260901', '2026-10-30')])
def test_bounded_past_window_before_any_sdk_call(start, end):
    _, _, _, calls, run = fixture()
    with pytest.raises(ValueError, match='breeze_date_range'):
        run(start=start, end=end)
    assert not calls
