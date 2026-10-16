import copy
import json

import pytest

from stock_discovery_analysis.revisions import Revision, adjusted_close, eligible, make_snapshot
from stock_discovery_analysis.revision_fixtures import fixture_records, CUTOFF, NOW


def changed(record, **changes):
    data=record.model_dump(mode='json')
    data.update(changes)
    return Revision.model_validate(data)


def snapshot(records=None, **changes):
    args=dict(mode='synthetic',cutoff=CUTOFF,created_at=NOW,
              universe_version='SYN-universe-1',calendar_version='SYN-calendar-1',stream_ids=['fixture'])
    args.update(changes)
    return make_snapshot(list(fixture_records() if records is None else records),**args)


def test_complete_fictional_snapshot_and_raw_adjusted_separation():
    snap=snapshot()
    assert snap.complete and snap.universe_total==snap.eligible_count==1
    candle=next(r for r in snap.revisions if r.data.kind=='candle')
    assert str(adjusted_close(candle,snap))=='52.5'
    assert candle.data.close=='105'
    assert snapshot().snapshot_id==snap.snapshot_id


def test_future_revision_and_late_fetch_are_excluded():
    records=list(fixture_records())
    candle=records[3]
    later=changed(candle,revision_id='SYN-later',source_revision='later',sequence=2,
                  supersedes_id=candle.revision_id,published_at='2026-10-16T10:00:00Z',
                  available_at='2026-10-16T10:01:00Z',fetched_at='2026-10-16T10:30:00Z',
                  data={**candle.data.model_dump(),'close':'106'})
    assert snapshot(records+[later]).snapshot_id==snapshot(records).snapshot_id
    observed=changed(candle,availability_basis='observed')
    assert not eligible(observed,'2026-10-14T11:00:00Z','live_paper')
    archived=changed(candle,availability_basis='verified_archive',archive_evidence_ref='fixture-proof',archive_revision_id=candle.revision_id)
    assert eligible(archived,'2026-10-14T11:00:00Z','historical_reconstructed')
    with pytest.raises(ValueError): changed(archived,archive_revision_id='different-revision')


def test_symbol_revision_does_not_rewrite_old_instrument_dependency():
    records=list(fixture_records())
    old=records[0]
    newer=changed(old,revision_id='SYN-renamed',source_revision='v2',sequence=2,
                  supersedes_id=old.revision_id,available_at='2026-10-15T10:00:00Z',
                  data={**old.data.model_dump(),'symbol':'RENAMED'})
    snap=snapshot(records+[newer])
    assert snap.complete and old in snap.dependencies
    assert newer in snap.revisions


@pytest.mark.parametrize('case', ['missing_candle','zero_volume','missing_calendar','missing_membership','incomplete_stream','unsupported_action'])
def test_partial_and_exclusion_states(case):
    rows=list(fixture_records())
    kwargs={}
    if case=='missing_candle': rows.pop(3)
    elif case=='zero_volume': rows[3]=changed(rows[3],data={**rows[3].data.model_dump(),'volume':0})
    elif case=='missing_calendar': rows.pop(2)
    elif case=='missing_membership': rows.pop(1)
    elif case=='incomplete_stream': kwargs['streams_complete']=False
    elif case=='unsupported_action': rows[4]=changed(rows[4],data={**rows[4].data.model_dump(),'action_type':'unsupported','share_ratio':None})
    snap=snapshot(rows,**kwargs)
    assert not snap.complete
    if case=='unsupported_action':
        assert snap.ineligible_count==1
        with pytest.raises(ValueError): adjusted_close(rows[3],snap)


def test_delisted_membership_kept_in_denominator_and_future_actions_not_applied():
    rows=list(fixture_records())
    rows[0]=changed(rows[0],data={**rows[0].data.model_dump(),'status':'delisted'})
    snap=snapshot(rows)
    assert snap.universe_total==snap.ineligible_count==1 and snap.eligible_count==0
    rows=list(fixture_records())
    rows[4]=changed(rows[4],data={**rows[4].data.model_dump(),'effective_at':'2026-10-16T03:45:00Z'})
    assert adjusted_close(rows[3],snapshot(rows))==105


@pytest.mark.parametrize('field,value', [('close','NaN'),('high','99'),('volume',True),('volume',-1),('adjustment_basis','adjusted'),('ends_at','2026-10-15T10:00:00Z')])
def test_bad_candles_rejected(field,value):
    r=fixture_records()[3]
    with pytest.raises(ValueError): changed(r,data={**r.data.model_dump(),field:value})


def test_unknown_fields_source_ambiguity_and_snapshot_clock():
    r=fixture_records()[3]
    with pytest.raises(ValueError): changed(r,unexpected=True)
    other=changed(r,revision_id='SYN-other',source_id='SYN-other')
    with pytest.raises(ValueError,match='ambiguous source'): snapshot(list(fixture_records())+[other])
    with pytest.raises(ValueError): snapshot(cutoff='2026-10-16T12:00:00Z')



def test_changed_session_open_is_not_silently_accepted():
    rows=list(fixture_records())
    rows[2]=changed(rows[2],data={**rows[2].data.model_dump(),'opens_at':'2026-10-14T04:00:00Z'})
    snap=snapshot(rows)
    assert not snap.complete and 'missing_sessions:SYN-listing' in snap.issues
