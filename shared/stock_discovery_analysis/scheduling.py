"""D3-04 exchange-calendar occurrences and honest coverage; pure functions."""
from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from pydantic import Field, model_validator

from stock_discovery_contracts.v2 import Hash, Mode, Profile, Ref, Strict, Text, Timestamp, check, digest

IST = ZoneInfo('Asia/Kolkata')


def utc(value):
    return datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)


def stamp(value):
    return value.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


class TradingSession(Strict):
    opens_at: Timestamp
    closes_at: Timestamp

    @model_validator(mode='after')
    def interval(self):
        check(utc(self.opens_at) < utc(self.closes_at), 'session interval')
        check(utc(self.opens_at).astimezone(IST).date() == utc(self.closes_at).astimezone(IST).date(), 'session crosses local date')
        return self


class ScheduleCalendar(Strict):
    ref: Ref
    available_at: Timestamp
    # Explicit coverage, including holidays: never infer closure from a truncated list.
    starts_on: str
    ends_on: str
    sessions: Annotated[tuple[TradingSession, ...], Field(min_length=1, max_length=400)]

    @model_validator(mode='after')
    def validity(self):
        start, end = date.fromisoformat(self.starts_on), date.fromisoformat(self.ends_on)
        check(start <= end, 'calendar coverage')
        check(self.ref.content_hash == digest([s.model_dump() for s in self.sessions]), 'calendar hash mismatch')
        for s in self.sessions:
            check(start <= utc(s.opens_at).astimezone(IST).date() <= end, 'session outside coverage')
        check(all(utc(a.closes_at) < utc(b.opens_at) for a,b in zip(self.sessions,self.sessions[1:])), 'unordered sessions')
        return self


class SchedulePolicy(Strict):
    version: Text
    ready_delay_minutes: Literal[30]
    readiness_retry_minutes: Literal[15]
    swing_stop_before_open_minutes: Literal[60]
    # Explicit configured expiry for longer-horizon jobs, not inferred capital policy.
    short_term_window_minutes: Annotated[int, Field(ge=15, le=10080)]
    long_term_window_minutes: Annotated[int, Field(ge=15, le=44640)]
    event_window_start_hour: Literal[8]
    event_window_end_hour: Literal[20]
    max_events_per_call: Annotated[int, Field(ge=1, le=100)]


class ScheduleConfig(Strict):
    schema_version: Literal['1.0.0']
    schedule_id: Text
    scope_id: Text
    input_hash: Hash
    code_version: Text
    mode: Mode
    calendar: ScheduleCalendar
    policy: SchedulePolicy
    horizons: Annotated[tuple[Profile, ...], Field(min_length=1, max_length=3)]
    starts_on: str

    @model_validator(mode='after')
    def bounds(self):
        check(len(set(self.horizons)) == len(self.horizons), 'duplicate horizons')
        start=date.fromisoformat(self.starts_on)
        check(date.fromisoformat(self.calendar.starts_on) <= start <= date.fromisoformat(self.calendar.ends_on), 'schedule outside calendar')
        return self


class Occurrence(Strict):
    occurrence_id: Hash
    schedule_hash: Hash
    schedule_id: Text
    scope_id: Text
    input_hash: Hash
    code_version: Text
    calendar_ref: Ref
    policy_hash: Hash
    policy: SchedulePolicy
    mode: Mode
    kind: Literal['discovery', 'event_poll']
    horizon: Profile | None
    information_cutoff_at: Timestamp
    due_at: Timestamp
    expires_at: Timestamp

    @model_validator(mode='after')
    def identity(self):
        check(utc(self.information_cutoff_at) <= utc(self.due_at) < utc(self.expires_at), 'occurrence interval')
        check((self.kind == 'discovery') == (self.horizon is not None), 'occurrence horizon')
        check(self.policy_hash == digest(self.policy.model_dump()), 'occurrence policy hash')
        wire = self.model_dump(mode='json')
        check(self.occurrence_id == digest({k:v for k,v in wire.items() if k != 'occurrence_id'}), 'occurrence hash')
        return self


def occurrence(config, kind, horizon, cutoff, due, expires):
    fields=dict(schedule_hash=digest(config.model_dump(mode='json')),
                schedule_id=config.schedule_id,scope_id=config.scope_id,
                input_hash=config.input_hash,code_version=config.code_version,
                calendar_ref=config.calendar.ref,policy_hash=digest(config.policy.model_dump()),policy=config.policy,
                mode=config.mode,kind=kind,horizon=horizon,
                information_cutoff_at=stamp(cutoff),due_at=stamp(due),expires_at=stamp(expires))
    wire={**fields,'calendar_ref':config.calendar.ref.model_dump(),'policy':config.policy.model_dump()}
    return Occurrence(occurrence_id=digest(wire),**fields)


def resolve_occurrences(config: ScheduleConfig, now: str):
    """Return due discovery slots; unavailable/truncated calendars fail closed."""
    clock=utc(now)
    check(utc(config.calendar.available_at) <= clock, 'calendar not yet available')
    result=[]
    sessions=config.calendar.sessions
    end=date.fromisoformat(config.calendar.ends_on)
    start=date.fromisoformat(config.starts_on)
    for index,s in enumerate(sessions):
        close=utc(s.closes_at)
        day=close.astimezone(IST).date()
        due=close+timedelta(minutes=config.policy.ready_delay_minutes)
        if day < start or due > clock:
            continue
        week_end=day+timedelta(days=6-day.weekday())
        month_end=(day.replace(day=28)+timedelta(days=4)).replace(day=1)-timedelta(days=1)
        next_day=utc(sessions[index+1].opens_at).astimezone(IST).date() if index+1<len(sessions) else None
        for horizon in config.horizons:
            if horizon=='swing':
                if next_day is None:
                    continue  # No next open means no safe publication window.
                expires=utc(sessions[index+1].opens_at)-timedelta(minutes=60)
            elif horizon=='short_term':
                if end < week_end or (next_day is not None and next_day <= week_end):
                    continue
                expires=due+timedelta(minutes=config.policy.short_term_window_minutes)
            else:
                if end < month_end or (next_day is not None and next_day <= month_end):
                    continue
                expires=due+timedelta(minutes=config.policy.long_term_window_minutes)
            check(due < expires, 'empty publication window')
            result.append(occurrence(config,'discovery',horizon,close,due,expires))
    return tuple(sorted(result,key=lambda o:(o.due_at,o.horizon)))


def event_poll_slots(config: ScheduleConfig, start: str, now: str):
    """Bounded due polling slots: 08–20 IST and one hour before each open."""
    first,last=utc(start),utc(now)
    check(first <= last and last-first <= timedelta(days=31), 'event catch-up bound')
    check(utc(config.calendar.available_at) <= last, 'calendar not yet available')
    times=set()
    day=first.astimezone(IST).date()
    while day <= last.astimezone(IST).date():
        if date.fromisoformat(config.starts_on) <= day <= date.fromisoformat(config.calendar.ends_on):
            for hour in range(8,21):
                times.add(datetime.combine(day,time(hour),IST).astimezone(timezone.utc))
        day+=timedelta(days=1)
    for s in config.calendar.sessions:
        if utc(s.opens_at).astimezone(IST).date() >= date.fromisoformat(config.starts_on):
            times.add(utc(s.opens_at)-timedelta(hours=1))
    return tuple(occurrence(config,'event_poll',None,t,t,t+timedelta(hours=1))
                 for t in sorted(times) if first < t <= last and utc(config.calendar.available_at)<=t)


def monitoring_active(config, now):
    clock=utc(now)
    day=clock.astimezone(IST).date()
    if not date.fromisoformat(config.starts_on)<=day<=date.fromisoformat(config.calendar.ends_on):
        return False
    local=clock.astimezone(IST)
    return utc(config.calendar.available_at) <= clock and (time(8) <= local.time() <= time(20) or any(utc(s.opens_at)-timedelta(hours=1) <= clock < utc(s.opens_at) for s in config.calendar.sessions))


Count=Annotated[int,Field(ge=0)]


class Coverage(Strict):
    universe_total: Count
    ineligible: Count
    eligible: Count
    screened: Count
    unscreened: Count
    candidate: Count
    noncandidate: Count
    research_complete: Count
    research_pending: Count
    research_failed: Count
    research_not_selected: Count
    data_complete: Count
    exclusion_reasons: tuple[Text, ...]

    @model_validator(mode='after')
    def reconciled(self):
        check(self.universe_total==self.ineligible+self.eligible, 'universe denominator')
        check(self.eligible==self.screened+self.unscreened, 'screening denominator')
        check(self.screened==self.candidate+self.noncandidate, 'candidate denominator')
        check(self.candidate==self.research_complete+self.research_pending+self.research_failed+self.research_not_selected, 'research denominator')
        check(self.data_complete<=self.eligible, 'data completeness')
        check(not self.ineligible or len(self.exclusion_reasons)>=self.ineligible, 'missing exclusion reasons')
        return self


def coverage_label(coverage, status):
    if status=='completed' and coverage.universe_total>0 and coverage.unscreened==0 and coverage.research_pending==0 and coverage.research_failed==0 and coverage.research_not_selected==0 and coverage.data_complete==coverage.eligible:
        return 'no_qualifying_picks' if coverage.candidate==0 else 'complete'
    return {'blocked':'blocked','failed':'failed','partial':'partial','missed':'missed'}.get(status,'incomplete')


def calendar_issues(config, now):
    """Expose missing planning coverage instead of reporting an empty successful scan."""
    day = utc(now).astimezone(IST).date()
    issues = []
    if utc(config.calendar.available_at) > utc(now):
        issues.append('calendar_not_available')
    if not any(utc(s.opens_at) > utc(now) for s in config.calendar.sessions):
        issues.append('next_session_unavailable')
    if day > date.fromisoformat(config.calendar.ends_on):
        issues.append('calendar_expired')
    return tuple(issues)


class ListingCoverage(Strict):
    listing_id: Text
    eligible: bool
    exclusion_reason: Text | None
    data_complete: bool
    stage: Literal['ineligible', 'unscreened', 'noncandidate', 'research_complete',
                   'research_pending', 'research_failed', 'research_not_selected']

    @model_validator(mode='after')
    def consistency(self):
        check(self.eligible == (self.stage != 'ineligible'), 'eligibility stage mismatch')
        check(self.eligible or bool(self.exclusion_reason), 'excluded listing needs reason')
        check(not self.data_complete or self.eligible, 'ineligible data denominator')
        check(self.stage in ('ineligible','unscreened') or self.data_complete, 'screened incomplete input')
        return self


def reconcile_universe(frozen_listing_ids, rows):
    """Exactly one result for EVERY frozen member, including omissions and exclusions."""
    check(len(set(frozen_listing_ids)) == len(frozen_listing_ids), 'duplicate frozen member')
    check(len({r.listing_id for r in rows}) == len(rows), 'duplicate coverage row')
    check(set(frozen_listing_ids) == {r.listing_id for r in rows}, 'coverage does not match frozen universe')
    def count(stage):
        return sum(r.stage == stage for r in rows)
    eligible = sum(r.eligible for r in rows)
    screened = eligible-count('unscreened')
    return Coverage(universe_total=len(rows),ineligible=count('ineligible'),eligible=eligible,
        screened=screened,unscreened=count('unscreened'),candidate=screened-count('noncandidate'),
        noncandidate=count('noncandidate'),research_complete=count('research_complete'),
        research_pending=count('research_pending'),research_failed=count('research_failed'),
        research_not_selected=count('research_not_selected'),data_complete=sum(r.data_complete for r in rows),
        exclusion_reasons=tuple(r.listing_id+':'+r.exclusion_reason for r in rows if not r.eligible))
