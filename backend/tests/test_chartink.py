from datetime import datetime, timezone
import pytest
from stock_discovery_analysis.chartink import Scanner, normalize, fixture_snapshot

NOW=datetime(2026,11,5,13,tzinfo=timezone.utc)


def scanner():
    return Scanner(scan_name='EOD Swing Candidates',scan_url='eod-swing-candidates',alert_name='Swing',
        version='1',rules='Synthetic discovery rules',rights_reference='SYNTHETIC TEST ONLY',
        enabled_until='2027-01-01T00:00:00Z',mode='synthetic_fixture')


def payload():
    return dict(stocks='INFY, M&M',trigger_prices='1500,200',triggered_at='6:00 pm',
        scan_name='EOD Swing Candidates',scan_url='eod-swing-candidates',alert_name='Swing',
        webhook_url='https://receiver.invalid/hooks/chartink/SECRET')


def test_documented_payload_never_claims_snapshot_or_provider_date():
    e=normalize(payload(),scanner(),NOW)
    assert e['symbols']==['INFY','M&M']
    assert e['session_date']=='2026-11-05' and e['event_at'] is None
    assert e['completeness']=='partial_unverified' and not e['evaluation_eligible']
    assert 'SECRET' not in str(e) and 'webhook_url' not in e['payload']
    assert normalize(payload(),scanner(),NOW.replace(minute=10))['event_id']==e['event_id']


@pytest.mark.parametrize('changes',[
    {'stocks':''},{'stocks':'NSE:INFY'},{'stocks':'INFY,infy'},
    {'stocks':'INFY','trigger_prices':'NaN'},{'trigger_prices':'1'},
    {'triggered_at':'2026-11-05T13:00:00Z'},{'triggered_at':'13:00 pm'},
    {'triggered_at':'6:99 pm'},{'scan_url':'other'},{'stocks':['INFY']},
    {'complete':True},{'stocks':'A'*31},{'trigger_prices':'Infinity,2'},
])
def test_malformed(changes):
    with pytest.raises(ValueError):normalize({**payload(),**changes},scanner(),NOW)


def test_fixture_labels_and_expiration():
    e=fixture_snapshot(scanner(),['INFY'],'2026-11-04',NOW,complete=True)
    assert e['mode']=='synthetic_fixture' and e['completeness']=='verified_fixture_snapshot'
    with pytest.raises(ValueError):normalize(payload(),scanner(),datetime(2027,1,1,tzinfo=timezone.utc))
    with pytest.raises(ValueError):fixture_snapshot(scanner().model_copy(update={'mode':'provider_alert'}),['INFY'],'2026-11-04',NOW)


def test_csv_adapter_counts_unverified_and_never_certifies_a_day():
    from stock_discovery_analysis.candidate_csv import events
    raw=b'Date,Symbol\n2026-11-04,INFY\n2026-11-05,INFY\n2026-11-05,M&M\n2026-11-05,INFY\n'
    e,s=events(raw,scanner(),NOW)
    assert (s['rows'],s['matches'],s['stocks'],s['sessions'])==(4,3,2,2)
    assert all(x['completeness']=='partial_unverified' and not x['historical_pit_qualified'] for x in e)
    assert all('trigger_prices' not in x['payload'] for x in e)
    assert events(raw,scanner(),NOW)[0]==e
    with pytest.raises(ValueError):events(b'Date,Wrong\n',scanner(),NOW)


def test_scanner_identity_survives_credential_and_authorization_renewal():
    s=scanner()
    assert s.key==s.model_copy(update={'rights_reference':'renewed approval','enabled_until':datetime(2028,1,1,tzinfo=timezone.utc)}).key
    assert s.key!=s.model_copy(update={'rules':'changed rules require a new version'}).key
