"""STK-083 stored-only adapter for the existing D3-04 scheduler; no provider clients."""
from stock_discovery_contracts.v2 import check,digest
from stock_discovery_analysis.daily_insight import research,VERSION,LISTING,ACQUISITION
from stock_discovery_analysis.real_views import ViewConfig
from stock_discovery_analysis.scheduling import calendar_issues


def handlers(schedule,view):
    view=ViewConfig.model_validate(view)
    check(view.listing_ids==(LISTING,), 'stored_research_infy_only')
    check(view.pilot_scope_id and view.pilot_scope_id.startswith('STK-083-INFY-'), 'isolated_stored_research_scope_required')
    check(schedule.mode=='live_paper' and schedule.scope_id==view.pilot_scope_id
          and schedule.input_hash==digest(view.model_dump(mode='json')) and schedule.horizons==('swing',),'stored_research_schedule_mismatch')
    def execute(conn,job,clock):
        # Catch-up describes evidence available NOW, never reconstructs a missed forecast.
        issues=calendar_issues(schedule,clock())
        if issues:
            return dict(status='partial',version=VERSION,report_state='analysis_unavailable',reasons=issues,
                evaluated_at=clock(),acquisition=dict(ACQUISITION),actionable=False),None
        result=research(conn,view,LISTING,clock=clock)
        closed=[s.closes_at for s in schedule.calendar.sessions if s.closes_at<=clock()]
        verified=result['market']['freshness']['latest_verified_closed_session']
        if closed and (verified is None or max(closed)>verified):
            return dict(status='partial',version=VERSION,report_state='analysis_unavailable',
                reasons=['scheduled_session_not_in_guarded_stored_calendar'],evaluated_at=clock(),
                acquisition=dict(ACQUISITION),actionable=False),None
        return dict(status='completed' if result['state'] in ('current_descriptive','delayed_descriptive') else 'partial',
            version=VERSION,report_id=result['report_id'],report_state=result['state'],evaluated_at=result['evaluated_at'],
            evidence_hash=result['evidence_hash'],catch_up=job['payload']['catch_up'],
            original_scheduled_cutoff=job['payload']['information_cutoff_at'],
            acquisition=dict(ACQUISITION),model_requests=0,actionable=False),None
    def poll(conn,job,clock):return dict(status='completed',version=VERSION,reason='stored_only_no_event_acquisition',actionable=False),None
    return {'ingest':execute,'event_poll':poll}
