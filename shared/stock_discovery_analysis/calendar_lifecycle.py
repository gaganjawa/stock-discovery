"""STK-086 / D3-04: inspect existing coverage, never infer exchange sessions.

Positive session revisions can corroborate a calendar, but cannot attest closed
dates or extend its explicit coverage. Provider renewal remains a separate,
owner-authorized operation in pilot_operations.renew_calendar.
"""
from datetime import date, timedelta
from .scheduling import IST, utc, stamp, calendar_issues


def lifecycle(schedule, now, *, warning_days=4):
    calendar = schedule.calendar
    today = utc(now).astimezone(IST).date()
    reasons = list(calendar_issues(schedule, now))
    future = [s for s in calendar.sessions if utc(s.opens_at) > utc(now)]
    pending = [(i, s) for i, s in enumerate(calendar.sessions)
               if utc(s.closes_at).astimezone(IST).date().isoformat() >= schedule.starts_on
               and utc(s.closes_at) + timedelta(minutes=schedule.policy.ready_delay_minutes) > utc(now)]
    next_due = None
    if pending:
        index, session = pending[0]
        next_due = stamp(utc(session.closes_at) + timedelta(minutes=schedule.policy.ready_delay_minutes))
        if index + 1 == len(calendar.sessions):
            reasons.append('next_execution_opening_unverified')
    else:
        reasons.append('next_execution_unverified')
    remaining = (date.fromisoformat(calendar.ends_on) - today).days
    warnings = ['calendar_expiring_soon'] if 0 <= remaining <= warning_days else []
    return dict(state='expired' if remaining < 0 else 'blocked' if reasons else 'expiring_soon' if warnings else 'valid',
                coverage_start=calendar.starts_on, coverage_end=calendar.ends_on,
                calendar_ref=calendar.ref.model_dump(mode='json'), available_at=calendar.available_at,
                next_verified_opening=future[0].opens_at if future else None,
                next_scheduled_execution=next_due, reasons=sorted(set(reasons)), warnings=warnings,
                completeness='existing_explicit_coverage_not_exchange_authority',
                renewal=dict(status='RENEWAL_BLOCKED',
                    reasons=['closed_date_coverage_not_in_session_revisions',
                             'recurring_calendar_acquisition_not_authorized'],
                    provider_requests=0, stored_sessions_available=False))
