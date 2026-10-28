"""STK-014: invented observations, never provider acceptance evidence."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

import pytest
from stock_discovery_contracts.rights import Grant, UseRequest
from stock_discovery_analysis.calendar import Calendar, Session
from stock_discovery_analysis.data import Candle, Provenance
from stock_discovery_analysis.swing_qualification import InputEvidence, SwingInputs, SCOPES, qualify


def fixture():
    cutoff = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)
    stamp = lambda d: d.strftime('%Y-%m-%dT%H:%M:%SZ')
    # Calendar is invented deliberately; this is not an exchange holiday claim.
    sessions = tuple(Session(cutoff-timedelta(days=i,hours=5), cutoff-timedelta(days=i,hours=1)) for i in range(29,-1,-1))
    prov = Provenance('test-provider', 'upstream-price-v1', cutoff, cutoff, cutoff, 'observed_live')
    bars = tuple(Candle('NSE:TEST', s.opens_at, s.closes_at, D(100), D(102), D(99), D(101), 1000, prov) for s in sessions)
    grant = Grant(schema_version='1.0.0', grant_id='test-grant', version='1', source_id='test-provider',
        account_ref='test-account', status='active', synthetic=False, approval_evidence_ref='TEST-ONLY',
        valid_from_at='2026-01-01T00:00:00Z', expires_at='2027-01-01T00:00:00Z', revoked_at=None,
        allowed_uses=('acquire','store','derive'), scopes=tuple(SCOPES.values()), regions=('IN',),
        external_processors=(), retention_days=30, deletion_deadline_days=0, attribution='TEST-ONLY',
        max_units_per_operation=100, audit_tombstones_permitted=False)
    rows = tuple(InputEvidence(requirement=name, instrument_id='NSE:TEST',
        revision_id='price-revision' if name=='prices' else name+'-revision', grant=grant,
        acquisition_grant_id=grant.grant_id, acquisition_grant_version=grant.version,
        acquisition_grant=grant, acquired_at=stamp(cutoff),
        revision_provenance=prov if name=='prices' else replace(prov,source_version='upstream-'+name+'-v1'),
        request=UseRequest(source_id='test-provider', account_ref='test-account', scope=scope,
            uses=('acquire','store','derive'), region='IN', destination_region=None, processor_ref=None,
            requested_at=stamp(cutoff), synthetic=False, units=1, retention_days=30, attribution_present=True),
        observed_at=stamp(cutoff), covers_from=stamp(sessions[0].opens_at), covers_through=stamp(cutoff),
        fresh_until=stamp(cutoff), complete=True, policy_evidence_ref='TEST-ONLY',
        retention_compliant=True, deletion_obligations_supported=True, fences_open=True) for name,scope in SCOPES.items())
    price_rows=tuple(rows[0].model_copy(update={'revision_id':f'price-revision-{i:02d}'}) for i in range(len(bars)))
    rows=price_rows+rows[1:]
    return SwingInputs(instrument_id='NSE:TEST', cutoff_at=stamp(cutoff), evidence=rows, bars=bars,
        bar_revision_ids=tuple(r.revision_id for r in price_rows), calendar_revision_id='calendar-revision',
        calendar=Calendar('test-calendar', sessions, replace(prov,source_version='upstream-calendar-v1')),
        price_basis='raw', volume_basis='raw', action_free_window=True, tick_size=D('.05'),
        lot_size=1, eligible=True, risk_prohibited=False)


def change_evidence(q, requirement, **changes):
    return q.model_copy(update={'evidence':tuple(r.model_copy(update=changes) if r.requirement==requirement else r for r in q.evidence)})


def test_qualified_inputs_never_authorize_execution_and_roundtrip():
    q=fixture()
    result=qualify(SwingInputs.model_validate_json(q.model_dump_json()))
    assert result.status=='INPUTS_QUALIFIED'
    assert not result.actionable and not result.publication_authorized and not result.paper_admission_authorized
    assert len(result.provenance)==35
    assert len(set(q.bar_revision_ids))==30
    assert result==qualify(q.model_copy(update={'evidence':tuple(reversed(q.evidence))}))


@pytest.mark.parametrize('requirement,changes,reason', [
    ('prices', {'grant':None}, 'rights:grant_missing'),
    ('prices', {'retention_compliant':None}, 'retention_deletion_unverified'),
    ('prices', {'deletion_obligations_supported':False}, 'retention_deletion_unverified'),
    ('corporate_actions', {'complete':False}, 'coverage_stale_incomplete_or_future'),
    ('calendar', {'fresh_until':'2026-10-19T12:00:00Z'}, 'coverage_stale_incomplete_or_future'),
    ('filings', {'complete':False}, 'coverage_stale_incomplete_or_future'),
    ('material_events', {'complete':False}, 'coverage_stale_incomplete_or_future'),
    ('prices', {'fences_open':None}, 'restriction_state_unverified_or_fenced'),
    ('prices', {'observed_at':'2026-10-21T12:00:00Z'}, 'coverage_stale_incomplete_or_future'),
])
def test_evidence_failures(requirement,changes,reason):
    result=qualify(change_evidence(fixture(),requirement,**changes))
    assert result.status=='INSUFFICIENT_EVIDENCE'
    assert reason in result.checks[requirement]


@pytest.mark.parametrize('changes,category,reason', [
    ({'price_basis':'split_bonus_adjusted'}, 'adjustments','unsupported_adjustment_basis'),
    ({'volume_basis':'unknown'}, 'adjustments','unsupported_adjustment_basis'),
    ({'tick_size':None}, 'settings','instrument_settings_or_eligibility_unknown_or_prohibited'),
    ({'lot_size':None}, 'settings','instrument_settings_or_eligibility_unknown_or_prohibited'),
    ({'eligible':None}, 'settings','instrument_settings_or_eligibility_unknown_or_prohibited'),
    ({'risk_prohibited':True}, 'settings','instrument_settings_or_eligibility_unknown_or_prohibited'),
    ({'action_free_window':None}, 'adjustments','action_effects_unqualified'),
])
def test_input_failures(changes,category,reason):
    result=qualify(fixture().model_copy(update=changes))
    assert result.status=='INSUFFICIENT_EVIDENCE' and reason in result.checks[category]


@pytest.mark.parametrize('requirement',list(SCOPES))
def test_missing_evidence(requirement):
    q=fixture()
    result=qualify(q.model_copy(update={'evidence':tuple(r for r in q.evidence if r.requirement!=requirement)}))
    assert 'evidence_missing' in result.checks[requirement]


@pytest.mark.parametrize('kind',['short','lag','duplicate','unattributed','future','synthetic'])
def test_history(kind):
    q=fixture(); bars=q.bars
    if kind=='short': bars=bars[-29:]
    if kind=='lag': bars=bars[:-1]
    if kind=='duplicate': bars=bars+(bars[-1],)
    if kind in ('unattributed','future','synthetic'):
        changes={'source_version':'unlinked'} if kind=='unattributed' else {'fetched_at':bars[0].provenance.fetched_at+timedelta(days=1)} if kind=='future' else {'availability_basis':'fictional_fixture'}
        bars=(replace(bars[0],provenance=replace(bars[0].provenance,**changes)),)+bars[1:]
    assert qualify(q.model_copy(update={'bars':bars})).status=='INSUFFICIENT_EVIDENCE'


@pytest.mark.parametrize('kind',['fenced','account','version','permission','scope','expired'])
def test_mixed_sources_cannot_mask_restricted_dependency(kind):
    q=fixture(); original=q.evidence[0]
    grant=original.grant.model_copy(update={'source_id':'other','grant_id':'other-grant'})
    request=original.request.model_copy(update={'source_id':'other'})
    other=original.model_copy(update={'revision_id':'other-price','acquisition_grant_id':'other-grant','grant':grant,'request':request})
    if kind=='fenced': other=other.model_copy(update={'fences_open':False})
    if kind=='account': other=other.model_copy(update={'request':request.model_copy(update={'account_ref':'wrong'})})
    if kind=='version': other=other.model_copy(update={'grant':grant.model_copy(update={'version':'old','status':'denied'})})
    if kind=='permission': other=other.model_copy(update={'grant':grant.model_copy(update={'allowed_uses':('acquire',)})})
    if kind=='scope': other=other.model_copy(update={'grant':grant.model_copy(update={'scopes':('calendar',)})})
    if kind=='expired': other=other.model_copy(update={'grant':grant.model_copy(update={'expires_at':q.cutoff_at})})
    result=qualify(q.model_copy(update={'evidence':q.evidence+(other,)}))
    assert result.status=='INSUFFICIENT_EVIDENCE'
    assert any(p[2]=='other' for p in result.provenance)


def test_renewal_cannot_authorize_old_acquisition():
    q=fixture(); old=q.evidence[0]
    result=qualify(change_evidence(q,'prices',grant=old.grant.model_copy(update={'version':'2'})))
    assert result.checks['prices']==('acquisition_grant_mismatch',)
    assert result.status=='INSUFFICIENT_EVIDENCE'
    assert result.provenance[-1][-1]=='1'  # Original grant version, not renewal.


@pytest.mark.parametrize('field,value',[('tick_size',D('NaN')),('tick_size',D(0)),('lot_size',0),('lot_size',True)])
def test_malformed_settings_rejected(field,value):
    from pydantic import ValidationError
    raw=fixture().model_dump();raw[field]=value
    with pytest.raises(ValidationError):
        SwingInputs.model_validate(raw)


def test_review_acquisition_before_grant_validity():
    q=fixture()
    rows=tuple(r.model_copy(update={'observed_at':'2026-10-20T11:00:00Z',
        'grant':r.grant.model_copy(update={'valid_from_at':'2026-10-20T11:30:00Z'})}) for r in q.evidence)
    assert qualify(q.model_copy(update={'evidence':rows})).status=='INSUFFICIENT_EVIDENCE'


def test_review_stored_id_is_not_upstream_version():
    q=fixture()
    rows=tuple(r.model_copy(update={'revision_id':'stored-'+r.revision_id}) for r in q.evidence)
    # Updated contract supplies explicit links separately from upstream versions.
    updates={'evidence':rows}
    updates.update(bar_revision_ids=tuple('stored-'+x for x in q.bar_revision_ids),
                   calendar_revision_id='stored-'+q.calendar_revision_id)
    assert qualify(q.model_copy(update=updates)).status=='INPUTS_QUALIFIED'


def test_review_conflicting_original_ownership():
    q=fixture(); r=q.evidence[0]
    other=r.model_copy(update={'acquisition_grant_id':'second-grant',
        'grant':r.grant.model_copy(update={'grant_id':'second-grant','account_ref':'second-account'}),
        'request':r.request.model_copy(update={'account_ref':'second-account'})})
    assert qualify(q.model_copy(update={'evidence':q.evidence+(other,)})).status=='INSUFFICIENT_EVIDENCE'


@pytest.mark.parametrize('valid_from,expires,reason',[
    ('2026-10-20T12:00:01Z','2027-01-01T00:00:00Z','grant_not_yet_valid'),
    ('2026-01-01T00:00:00Z','2026-10-20T12:00:00Z','grant_expired'),
    ('2026-10-20T12:00:00Z','2026-10-20T12:00:01Z',None),
])
def test_original_acquisition_validity_boundaries(valid_from,expires,reason):
    q=fixture(); original=q.evidence[0].acquisition_grant.model_copy(update={'valid_from_at':valid_from,'expires_at':expires})
    result=qualify(change_evidence(q,'prices',acquisition_grant=original))
    if reason:
        assert 'acquisition_rights:'+reason in result.checks['prices']
        assert result.status=='INSUFFICIENT_EVIDENCE'
    else: assert result.status=='INPUTS_QUALIFIED'


@pytest.mark.parametrize('changes,reason',[
    ({'expires_at':'2026-10-20T12:00:00Z'},'grant_expired'),
    ({'status':'revoked','revoked_at':'2026-10-20T12:00:00Z'},'grant_not_active'),
    ({'allowed_uses':('acquire','store')},'use_denied'),
])
def test_current_use_independent_of_lawful_acquisition(changes,reason):
    q=fixture(); current=q.evidence[0].grant.model_copy(update=changes)
    result=qualify(change_evidence(q,'prices',grant=current))
    assert 'rights:'+reason in result.checks['prices']
    assert not any(x.startswith('acquisition_rights:') for x in result.checks['prices'])


def test_current_store_derive_need_not_include_new_acquisition_permission():
    q=fixture(); current=q.evidence[0].grant.model_copy(update={'allowed_uses':('store','derive')})
    assert qualify(change_evidence(q,'prices',grant=current)).status=='INPUTS_QUALIFIED'


@pytest.mark.parametrize('changes,reason',[
    ({'acquired_at':None},'acquisition_provenance_missing'),
    ({'revision_provenance':None},'acquisition_provenance_missing'),
    ({'acquisition_grant':None},'acquisition_rights:grant_missing'),
    ({'acquired_at':'2026-10-20T11:59:59Z'},'acquisition_timestamp_conflict'),
    ({'observed_at':'2026-10-20T11:59:59Z'},'acquisition_timestamp_conflict'),
    ({'acquired_at':'2026-10-20T12:00:01Z'},'acquisition_timestamp_conflict'),
])
def test_acquisition_timestamps(changes,reason):
    result=qualify(change_evidence(fixture(),'prices',**changes))
    assert reason in result.checks['prices']
    assert result.status=='INSUFFICIENT_EVIDENCE'


@pytest.mark.parametrize('field',['provider','account','grant','version','provenance','acquired_at','instrument'])
def test_conflicting_revision_identity_order_independent(field):
    q=fixture(); row=q.evidence[0]
    changes={
        'provider':{'request':row.request.model_copy(update={'source_id':'other'})},
        'account':{'request':row.request.model_copy(update={'account_ref':'other'})},
        'grant':{'acquisition_grant_id':'other'},
        'version':{'acquisition_grant_version':'other'},
        'provenance':{'revision_provenance':replace(row.revision_provenance,source_version='other')},
        'acquired_at':{'acquired_at':'2026-10-20T11:59:59Z'},
        'instrument':{'instrument_id':'NSE:OTHER'},
    }[field]
    rows=q.evidence+(row.model_copy(update=changes),)
    result=qualify(q.model_copy(update={'evidence':rows}))
    assert 'conflicting_immutable_acquisition' in result.checks['prices']
    assert result==qualify(q.model_copy(update={'evidence':tuple(reversed(rows))}))


def test_identical_references_are_idempotent():
    q=fixture()
    assert qualify(q)==qualify(q.model_copy(update={'evidence':q.evidence+q.evidence}))


@pytest.mark.parametrize('changes',[
    {'bar_revision_ids':()},
    {'bar_revision_ids':('wrong',)*30},
    {'calendar_revision_id':None},
    {'calendar_revision_id':'price-revision'},
])
def test_explicit_revision_links_required(changes):
    assert qualify(fixture().model_copy(update=changes)).status=='INSUFFICIENT_EVIDENCE'


def test_linked_wrong_upstream_version_denied():
    q=fixture(); row=q.evidence[0]
    result=qualify(change_evidence(q,'prices',revision_provenance=replace(row.revision_provenance,source_version='wrong')))
    assert 'price_source_unattributed' in result.checks['prices']


def test_conflicting_provenance_remains_in_diagnostics():
    q=fixture(); r=q.evidence[0]
    other=r.model_copy(update={'revision_provenance':replace(r.revision_provenance,source_version='conflicting-upstream')})
    result=qualify(q.model_copy(update={'evidence':q.evidence+(other,)}))
    assert {p[2] for p in result.revision_lineage if p[0]==r.revision_id}=={'upstream-price-v1','conflicting-upstream'}


def test_thirty_sessions_cannot_share_one_immutable_revision():
    q=fixture()
    # Keep the original reviewed exploit even after the success fixture is fixed.
    rows=tuple(r for r in q.evidence if r.requirement!='prices')+(q.evidence[0],)
    q=q.model_copy(update={'evidence':rows,'bar_revision_ids':(q.evidence[0].revision_id,)*30})
    result=qualify(q)
    assert result.status=='INSUFFICIENT_EVIDENCE'
    assert 'conflicting_immutable_candle' in result.checks['prices']


@pytest.mark.parametrize('changes',[{'open':D(100.5)},{'high':D(103)},{'low':D(98)},
                                     {'close':D(101.5)},{'volume':1001}])
def test_same_revision_conflicting_candle_values(changes):
    q=fixture()
    q=q.model_copy(update={'bars':q.bars+(replace(q.bars[0],**changes),),
                          'bar_revision_ids':q.bar_revision_ids+(q.bar_revision_ids[0],)})
    result=qualify(q)
    assert 'conflicting_immutable_candle' in result.checks['prices']
    assert result.status=='INSUFFICIENT_EVIDENCE'
    assert result==qualify(q.model_copy(update={'bars':tuple(reversed(q.bars)),
        'bar_revision_ids':tuple(reversed(q.bar_revision_ids)), 'evidence':tuple(reversed(q.evidence))}))


def test_identical_candle_references_are_idempotent():
    q=fixture()
    assert qualify(q)==qualify(q.model_copy(update={'bars':q.bars+q.bars,
        'bar_revision_ids':q.bar_revision_ids+q.bar_revision_ids}))


def test_duplicate_references_do_not_make_thirty_sessions():
    q=fixture()
    bars=q.bars[:-1];ids=q.bar_revision_ids[:-1]
    result=qualify(q.model_copy(update={'bars':bars+bars,'bar_revision_ids':ids+ids}))
    assert result.status=='INSUFFICIENT_EVIDENCE'
    assert 'insufficient_history' in result.checks['history']


def test_reordered_linked_inputs_are_identical():
    q=fixture()
    assert qualify(q)==qualify(q.model_copy(update={'bars':tuple(reversed(q.bars)),
        'bar_revision_ids':tuple(reversed(q.bar_revision_ids)), 'evidence':tuple(reversed(q.evidence))}))
