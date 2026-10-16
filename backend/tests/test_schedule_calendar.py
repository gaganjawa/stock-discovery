import json
from datetime import timedelta
import pytest
from pydantic import ValidationError

from stock_discovery_contracts.v2 import digest
from stock_discovery_analysis.schedule_fixtures import fixture_config, handlers
from stock_discovery_analysis.scheduling import (Coverage, ScheduleConfig, calendar_issues, coverage_label,
    event_poll_slots, monitoring_active, resolve_occurrences, stamp, utc)


def config(**changes):
    wire = fixture_config().model_dump(mode='json')
    wire.update(changes)
    return ScheduleConfig.model_validate_json(json.dumps(wire))


def test_calendar_close_week_month_and_special_session():
    c = fixture_config()
    assert not resolve_occurrences(c,'2026-10-15T10:29:59Z')
    assert [o.horizon for o in resolve_occurrences(c,'2026-10-15T10:30:00Z')] == ['swing']
    slots = resolve_occurrences(c,'2026-10-19T10:30:00Z')
    assert [(o.information_cutoff_at[8:10],o.horizon) for o in slots] == [
        ('15','swing'),('16','short_term'),('16','swing'),('19','long_term'),('19','short_term')]
    assert slots[0].expires_at == '2026-10-16T02:45:00Z'
    wire = c.calendar.model_dump(mode='json')
    wire['sessions'][1] = dict(opens_at='2026-10-17T12:30:00Z',closes_at='2026-10-17T13:30:00Z')
    wire['ref']['content_hash'] = digest(wire['sessions'])
    special = config(calendar=wire)
    assert resolve_occurrences(special,'2026-10-17T14:00:00Z')[0].expires_at == '2026-10-17T11:30:00Z'
    assert resolve_occurrences(special,'2026-10-17T14:00:00Z')[1].due_at == '2026-10-17T14:00:00Z'


def test_calendar_revision_truncation_and_future_availability():
    c = fixture_config()
    wire = c.calendar.model_dump(mode='json')
    wire['ends_on']='2026-10-19'
    revised = config(calendar=wire)
    assert all(o.horizon != 'long_term' for o in resolve_occurrences(revised,'2026-10-20T00:00:00Z'))
    assert 'calendar_expired' in calendar_issues(revised,'2026-10-20T00:00:00Z')
    assert resolve_occurrences(c,'2026-10-16T12:00:00Z')[0].occurrence_id != resolve_occurrences(revised,'2026-10-16T12:00:00Z')[0].occurrence_id
    with pytest.raises(ValueError,match='not yet available'):
        resolve_occurrences(c,'2026-10-14T00:00:00Z')


@pytest.mark.parametrize('now,active',[('02:29:59',False),('02:30:00',True),('14:30:00',True),('14:30:01',False)])
def test_monitoring_hours(now,active):
    assert monitoring_active(fixture_config(),'2026-10-16T'+now+'Z') is active


def test_poll_slots_bounds_and_dedup():
    c = fixture_config()
    slots = event_poll_slots(c,'2026-10-16T00:00:00Z','2026-10-16T23:59:59Z')
    assert len(slots)==14  # hourly 08..20 plus 08:15 pre-open
    assert len({o.occurrence_id for o in slots})==14
    with pytest.raises(ValueError,match='bound'):
        event_poll_slots(c,'2026-09-01T00:00:00Z','2026-10-16T00:00:00Z')


def coverage(**changes):
    fields = dict(universe_total=2,ineligible=1,eligible=1,screened=1,unscreened=0,candidate=0,noncandidate=1,
        research_complete=0,research_pending=0,research_failed=0,research_not_selected=0,data_complete=1,
        exclusion_reasons=('SYN-excluded:suspended',))
    fields.update(changes)
    return Coverage(**fields)


@pytest.mark.parametrize('field',['universe_total','eligible','screened','candidate','research_complete','data_complete'])
def test_coverage_rejects_broken_denominators(field):
    with pytest.raises(ValidationError):
        coverage(**{field:10})


@pytest.mark.parametrize('status',['blocked','failed','partial','missed','running'])
def test_failure_never_no_picks(status):
    assert coverage_label(coverage(),status) != 'no_qualifying_picks'


def test_complete_and_incomplete_coverage():
    assert coverage_label(coverage(),'completed')=='no_qualifying_picks'
    assert coverage_label(coverage(data_complete=0),'completed')=='incomplete'
    with pytest.raises(ValidationError):
        coverage(exclusion_reasons=())
    with pytest.raises(ValidationError):
        config(horizons=['swing','swing'])
    with pytest.raises(ValueError):
        handlers(config(mode='live_paper'))


def test_frozen_universe_expansion_exclusions_and_partial_reconciliation():
    from stock_discovery_analysis.scheduling import ListingCoverage, reconcile_universe
    rows=(ListingCoverage(listing_id='A',eligible=True,exclusion_reason=None,data_complete=True,stage='research_pending'),
          ListingCoverage(listing_id='B',eligible=False,exclusion_reason='delisted',data_complete=False,stage='ineligible'),
          ListingCoverage(listing_id='C',eligible=True,exclusion_reason=None,data_complete=False,stage='unscreened'))
    result=reconcile_universe(('A','B','C'),rows)
    assert result.universe_total==3 and result.research_pending==1 and result.unscreened==1
    assert result.exclusion_reasons==('B:delisted',)
    with pytest.raises(ValueError,match='frozen universe'):
        reconcile_universe(('A','B','C','D'),rows)
    with pytest.raises(ValueError,match='duplicate'):
        reconcile_universe(('A','B','C'),rows+rows[:1])
