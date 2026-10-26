import gzip
import json
from types import SimpleNamespace
from datetime import datetime,timezone
import httpx
import pytest
from stock_discovery_analysis.revision_storage import Stream
from stock_discovery_analysis.revisions import InstrumentData
from worker.providers.upstox import Upstox,UpstreamAccessRejected,observed_revision,RevisionPages

NOW='2026-10-19T03:00:00Z'
S=Stream(stream_id='test-price',source_id='upstox',account_ref='test',scope='prices')
U=S.model_copy(update={'scope':'universe'})
ROW=dict(segment='NSE_EQ',exchange='NSE',instrument_type='EQ',trading_symbol='INFY',name='Infosys Limited',isin='INE009A01021',instrument_key='NSE_EQ|INE009A01021',lot_size=1,tick_size=5)


def identity():
    return observed_revision(InstrumentData(kind='instrument',issuer_id=ROW['isin'],symbol='INFY',isin=ROW['isin'],series='EQ',status='active',lot_size=1,tick_size='0.05',effective_at=NOW),listing='NSE:'+ROW['isin'],fetched=NOW)


def make(response,deny=False):
    calls=[];uses=[]
    def require(stream,requested):
        uses.append(requested)
        if deny:raise PermissionError('grant_missing')
    def handle(request):
        calls.append(request)
        return response
    access=SimpleNamespace(require=require,clock=lambda:NOW)
    return Upstox(access=access,token='test-only-not-a-credential',transport=httpx.MockTransport(handle)),calls,uses


def test_permission_denial_precedes_network():
    client,calls,uses=make(httpx.Response(200),deny=True)
    with pytest.raises(PermissionError):client.instruments(U,('INFY',))
    assert not calls


def test_resolve_exact_cash_equity_and_no_bearer_to_master():
    client,calls,_=make(httpx.Response(200,content=gzip.compress(json.dumps([ROW]).encode())))
    assert client.instruments(U,('INFY',))[0]['tick_size']=='0.05'
    assert 'authorization' not in calls[0].headers


@pytest.mark.parametrize('rows',[[ROW,ROW],[{**ROW,'instrument_type':'BE'}],[{**ROW,'instrument_key':'NSE_EQ|wrong'}]])
def test_reject_ambiguous_or_non_equity(rows):
    client,_,_=make(httpx.Response(200,content=gzip.compress(json.dumps(rows).encode())))
    with pytest.raises(ValueError):client.instruments(U,('INFY',))


def test_real_endpoint_daily_timezone_and_decimal_validation():
    # Fabricated contract response; not a real-market integration claim.
    client,calls,_=make(httpx.Response(200,json={'status':'success','data':{'candles':[['2026-10-16T00:00:00+05:30',100,110,90,105,123,0]]}}))
    bars=client.candles(S,identity(),'2026-10-15','2026-10-16',{'2026-10-16':('2026-10-16T03:45:00Z','2026-10-16T10:00:00Z')})
    assert bars[0][0].adjustment_basis=='split_bonus_adjusted'
    assert bars[0][0].close=='105' and bars[0][0].ends_at=='2026-10-16T10:00:00Z'
    assert '/v3/historical-candle/NSE_EQ%7CINE009A01021/days/1/2026-10-16/2026-10-15' in str(calls[0].url)
    assert calls[0].headers['authorization']=='Bearer test-only-not-a-credential'


def test_unverified_calendar_and_bad_volume_block():
    row=['2026-10-16T00:00:00+05:30',100,110,90,105,123,0]
    client,_,_=make(httpx.Response(200,json={'status':'success','data':{'candles':[row]}}))
    with pytest.raises(ValueError,match='unverified_market_session'):client.candles(S,identity(),'2026-10-15','2026-10-16',{})
    row[5]=True
    client,_,_=make(httpx.Response(200,json={'status':'success','data':{'candles':[row]}}))
    with pytest.raises(ValueError,match='invalid_volume'):client.candles(S,identity(),'2026-10-15','2026-10-16',{'2026-10-16':('2026-10-16T03:45:00Z','2026-10-16T10:00:00Z')})


@pytest.mark.parametrize('code',[401,403,429,500,302])
def test_provider_failures_are_sanitized(code):
    client,_,_=make(httpx.Response(code,text='sensitive provider response'))
    with pytest.raises((PermissionError,RuntimeError)) as error:client.instruments(U,('INFY',))
    assert 'sensitive' not in str(error.value)


@pytest.mark.parametrize('code,classification,reason',[
    (401,'upstox_authentication_rejected','credentials'),
    (403,'upstox_authorization_rejected','rights')])
def test_upstream_rejection_is_typed_sanitized_and_not_a_transient(code,classification,reason):
    from worker.real_pilot import safe_error,retryable_rows
    client,calls,_=make(httpx.Response(code,text='secret token/provider body'))
    try:
        with pytest.raises(UpstreamAccessRejected) as caught:
            client.session(S.model_copy(update={'scope':'calendar'}),'2026-10-16')
        assert len(calls)==1 and caught.value.status_code==code
        assert caught.value.reason==reason and safe_error(caught.value)==classification
        assert str(caught.value)=='upstox_credentials_rejected'  # Calendar compatibility.
        assert not retryable_rows([dict(status='failed',errors=[classification])])
        assert safe_error(PermissionError('grant_missing'))!=classification
    finally:client.close()


def test_revisions_preserve_first_observation_and_page():
    first=identity()
    assert observed_revision(first.data,listing=first.listing_id,fetched='2026-10-20T00:00:00Z',previous=first)==first
    changed=observed_revision(first.data.model_copy(update={'symbol':'RENAMED'}),listing=first.listing_id,fetched='2026-10-20T00:00:00Z',previous=first)
    assert changed.sequence==2 and changed.supersedes_id==first.revision_id
    assert changed.available_at=='2026-10-20T00:00:00Z'
    pages=RevisionPages((first,changed))
    assert pages.fetch(None,1).next_cursor=='1' and pages.fetch('1',1).complete


def test_dated_session_is_observed_not_inferred():
    client,_,_=make(httpx.Response(200,json={'status':'success','data':[]}))
    assert client.session(S.model_copy(update={'scope':'calendar'}),'2026-10-16') is None
    client,_,_=make(httpx.Response(200,json={'status':'success','data':[{'exchange':'NSE','start_time':0,'end_time':1000}]}))
    with pytest.raises(ValueError,match='session_date_mismatch'):
        client.session(S.model_copy(update={'scope':'calendar'}),'2026-10-16')


def test_adjustment_correction_appends_without_rewriting_old_observation():
    client,_,_=make(httpx.Response(200,json={'status':'success','data':{'candles':[['2026-10-16T00:00:00+05:30',100,110,90,105,123,0]]}}))
    data,fetched=client.candles(S,identity(),'2026-10-16','2026-10-16',{'2026-10-16':('2026-10-16T03:45:00Z','2026-10-16T10:00:00Z')})[0]
    old=observed_revision(data.model_copy(update={'adjustment_basis':'raw'}),listing=identity().listing_id,fetched=fetched,parent=identity().revision_id)
    new=observed_revision(data,listing=old.listing_id,fetched=fetched,parent=identity().revision_id,previous=old)
    assert old.data.adjustment_basis=='raw'
    assert new.sequence==2 and new.supersedes_id==old.revision_id
    from stock_discovery_analysis.revisions import eligible,adjusted_close
    assert not eligible(new,NOW,'historical_reconstructed')
    with pytest.raises(ValueError,match='provider_adjusted_candle_requires_action_coverage'):
        adjusted_close(new,SimpleNamespace(revisions=(new,)))
