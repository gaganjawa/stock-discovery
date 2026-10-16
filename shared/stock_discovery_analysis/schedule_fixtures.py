"""Explicit fictional unattended acceptance. Never selects real securities."""
from stock_discovery_contracts.v2 import digest
from .revision_fixtures import fixture_adapter, fixture_grant, fixture_records, fixture_request, fixture_stream
from .revision_storage import freeze_snapshot, ingest_next, read_snapshot
from .scheduling import Coverage, ScheduleConfig
from .schedule_runner import JobFailure
import json

SCOPES = ('universe','calendar','prices','corporate_actions','filings')


def fixture_config():
    sessions = [dict(opens_at=f'2026-10-{d}T03:45:00Z', closes_at=f'2026-10-{d}T10:00:00Z') for d in ('15','16','19')]
    return ScheduleConfig.model_validate_json(json.dumps(dict(schema_version='1.0.0',
        schedule_id='SYN-D304',scope_id='SYN-universe-1',
        input_hash=digest([r.model_dump(mode='json') for r in fixture_records()]),code_version='SYN-D304-v1',mode='synthetic',
        calendar=dict(ref=dict(id='SYN-calendar',version='1',content_hash=digest(sessions)),
                      available_at='2026-10-15T00:00:00Z',starts_on='2026-10-15',ends_on='2026-10-31',sessions=sessions),
        policy=dict(version='SYN-1',ready_delay_minutes=30,readiness_retry_minutes=15,swing_stop_before_open_minutes=60,
                    short_term_window_minutes=1440,long_term_window_minutes=1440,event_window_start_hour=8,event_window_end_hour=20,max_events_per_call=20),
        horizons=['swing','short_term','long_term'],starts_on='2026-10-15')))


def handlers(config):
    """Installed fixture adapter only; real sources cannot opt in by changing mode."""
    expected = fixture_config()
    if config.mode != 'synthetic' or config.input_hash != expected.input_hash or config.scope_id != expected.scope_id:
        raise ValueError('fictional adapter requires pinned synthetic fixture inputs')

    def requests(now):
        return {fixture_stream(s).stream_id:fixture_request(s,requested_at=now) for s in SCOPES}

    def ingest(conn, job, clock):
        for scope in SCOPES:
            adapter = fixture_adapter(scope)
            for _ in adapter.pages:
                ingest_next(conn,fixture_stream(scope),adapter,clock=clock,load_grant=fixture_grant,
                            request=fixture_request(scope,requested_at=clock()),audit=lambda d:None)
        return {'input_hash':config.input_hash}, 'snapshot'

    def snapshot(conn, job, clock):
        now = clock()
        snap = freeze_snapshot(conn,streams=tuple(fixture_stream(s) for s in SCOPES),load_grant=lambda s:fixture_grant(),
            requests=requests(now),audit=lambda d:None,mode='synthetic',cutoff=job['payload']['information_cutoff_at'],
            created_at=now,universe_version='SYN-universe-1',calendar_version='SYN-calendar-1')
        if not snap.complete:
            raise JobFailure('readiness')
        return {'snapshot_id':snap.snapshot_id}, 'screen'

    def screen(conn, job, clock):
        snap = read_snapshot(conn,job['payload']['extra']['snapshot_id'],load_grant=lambda s:fixture_grant(),
                             requests=requests(clock()),audit=lambda d:None)
        # Test-only classifier: every eligible fictional member is a noncandidate.
        # This is NOT the D3-05 investment policy and never produces a BUY.
        coverage = Coverage(universe_total=snap.universe_total,ineligible=snap.ineligible_count,eligible=snap.eligible_count,
            screened=snap.eligible_count,unscreened=0,candidate=0,noncandidate=snap.eligible_count,
            research_complete=0,research_pending=0,research_failed=0,research_not_selected=0,
            data_complete=snap.eligible_count,exclusion_reasons=tuple('ineligible:'+s for s in snap.excluded_listings))
        return {'coverage':coverage.model_dump(mode='json'),'fixture_only':True,'snapshot_id':snap.snapshot_id}, None

    def poll(conn, job, clock):
        return {'fixture_only':True,'events':0}, None

    return {'ingest':ingest,'snapshot':snapshot,'screen':screen,'event_poll':poll}
