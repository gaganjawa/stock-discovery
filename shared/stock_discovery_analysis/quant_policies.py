"""STK-028–032/054/058/076: deterministic quantitative policy boundary.

No source acquisition, AI, position sizing, or publication. Fixture policies are
never usable for real data. Wire values reuse D3-01 policy/evidence contracts.
"""
import calendar as month_calendar
from dataclasses import asdict
import json
from datetime import timedelta, timezone
from decimal import Decimal as D, localcontext, Context
from types import SimpleNamespace, MappingProxyType
from typing import Literal

from pydantic import model_validator
from stock_discovery_contracts.v2 import (
    Condition, Conditions, Evidence, Horizon, Number, Policy, Ref, Strict, Text,
    Timestamp, Valuation, at, check, digest, resolve_endpoint,
)
from .dataset import canonical
from .indicators import features
from .strategy import analyze as legacy_analyze, STRATEGY_VERSION

FORMULA_VERSION = 'quant-horizons-1.0.0'
COMMON = {'duration':'count','entry_sessions':'count','max_price_age_days':'days',
          'max_evidence_age_days':'days'}
FUNDAMENTAL = {'report_months':'months','max_statement_age_days':'days','min_revenue_growth':'ratio',
    'min_earnings_growth':'ratio','min_price_to_sma':'ratio','bear_pe':'multiple',
    'base_pe':'multiple','bull_pe':'multiple','min_margin_of_safety':'ratio'}
LONG = {'min_ocf_margin':'ratio','min_roe':'ratio','max_net_debt_to_ocf':'multiple',
        'durability_years':'count','min_fcf_yield':'ratio'}
SWING = {'forecast_sessions':'count'}
SUPPORTED = {'swing':COMMON | SWING, 'short_term':COMMON | FUNDAMENTAL,
             'long_term':COMMON | FUNDAMENTAL | LONG}


def wire_number(value):
    return format(value, 'f') if value is not None else None


class PolicyRegistry:
    """Append-only immutable wire snapshots; export/import for persisted manifests.

    Version reuse with different approval metadata or parameters is forbidden.
    No approved or live policy is bundled; approval_ref is supplied by governance.
    """
    def __init__(self):
        self._records = {}

    def register(self, policy: Policy):
        # Revalidate even model_copy/model_construct inputs; never trust mutable lists.
        policy = Policy.model_validate_json(policy.model_dump_json())
        check(policy.kind == 'strategy', 'strategy policy required')
        required = SUPPORTED[policy.profile]
        check({p.name:p.unit for p in policy.parameters} == required, 'policy parameters/units')
        values = {p.name:D(p.value) for p in policy.parameters if p.value is not None}
        if len(values) == len(required):
            bounds = {'swing':(2,10),'short_term':(1,3),'long_term':(1,5)}[policy.profile]
            check(values['duration'] == int(values['duration']) and bounds[0] <= values['duration'] <= bounds[1], 'duration')
            for name in ('entry_sessions','max_price_age_days','max_evidence_age_days','max_statement_age_days','durability_years','forecast_sessions'):
                if name in values:
                    check(values[name] == int(values[name]) and 0 < values[name] <= 3660, 'positive bounded integer setting')
            if policy.profile == 'swing':
                check(2 <= values['forecast_sessions'] <= 10, 'forecast sessions')
            else:
                check(values['report_months'] in (D(3),D(12)), 'report period')
                check(policy.profile != 'long_term' or values['report_months']==12, 'long-term annual quality history')
                check(0 < values['bear_pe'] <= values['base_pe'] <= values['bull_pe'], 'scenario ordering')
                check(0 <= values['min_margin_of_safety'] < 1, 'margin of safety')
                check(values['min_price_to_sma'] > 0, 'price confirmation')
                if policy.profile == 'long_term':
                    check(2 <= values['durability_years'] <= 5, 'durability history')
        record = policy.model_dump_json()
        key = (policy.ref.id, policy.ref.version)
        check(key not in self._records or self._records[key] == record, 'immutable policy version conflict')
        self._records[key] = record
        return digest(json.loads(record))

    def get(self, reference: Ref):
        raw = self._records.get((reference.id,reference.version))
        if raw is None:
            return None
        policy = Policy.model_validate_json(raw)
        check(policy.ref == reference, 'policy reference hash mismatch')
        return policy

    def export(self):
        return tuple(self._records[k] for k in sorted(self._records))

    @classmethod
    def restore(cls, records):
        registry = cls()
        for raw in records:
            registry.register(Policy.model_validate_json(raw))
        return registry


class Statement(Strict):
    revision_id: Text
    instrument_id: Text
    period_start_at: Timestamp
    period_end_at: Timestamp
    period_kind: Literal['annual', 'quarter']
    scope: Literal['consolidated', 'standalone']
    currency: Literal['INR']
    monetary_unit: Literal['INR']
    evidence: Evidence
    revenue: Number | None
    earnings: Number | None
    operating_cash_flow: Number | None
    capital_expenditure: Number | None
    debt: Number | None
    cash: Number | None
    equity: Number | None
    diluted_shares: Number | None

    @model_validator(mode='after')
    def consistency(self):
        check(self.instrument_id == self.evidence.instrument_id and self.revision_id == self.evidence.revision_id, 'statement provenance identity')
        check(self.evidence.kind == 'filing' and self.evidence.period_end_at == self.period_end_at, 'statement period provenance')
        check(at(self.period_start_at) < at(self.period_end_at) <= at(self.evidence.published_at), 'statement publication')
        days = (at(self.period_end_at)-at(self.period_start_at)).days
        check((330 <= days <= 371) if self.period_kind == 'annual' else (75 <= days <= 100), 'unsupported fiscal period')
        for name in ('revenue','capital_expenditure','debt','cash','diluted_shares'):
            value = getattr(self,name)
            check(value is None or D(value) >= 0, 'negative amount: '+name)
        return self


class CoverageCheck(Strict):
    requirement: Literal['actions', 'material_events', 'filings', 'governance', 'business']
    evidence: Evidence
    complete: bool
    adverse: bool


def available(evidence, cutoff, mode):
    check(at(evidence.published_at) <= at(evidence.available_at) <= at(evidence.fetched_at), 'evidence clock order')
    check(evidence.availability_basis != 'verified_archive' or bool(evidence.archive_verification_ref), 'archive verification required')
    if at(evidence.available_at) > at(cutoff):
        return False
    basis = {'synthetic':'fictional_fixture','live_paper':'observed','historical_reconstructed':'verified_archive'}[mode]
    return evidence.availability_basis == basis and (mode != 'live_paper' or at(evidence.fetched_at) <= at(cutoff))


def horizon_for(profile, values, calendar, cutoff):
    anchor = at(cutoff)
    check(calendar.provenance.eligible(anchor.replace(tzinfo=timezone.utc)), 'calendar unavailable')
    closes = [s.closes_at.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ') for s in calendar.sessions]
    duration = int(values['duration'])
    endpoint = resolve_endpoint(SimpleNamespace(profile=profile,duration=duration,anchor_at=cutoff),closes)
    future = [s for s in closes if at(s)>anchor]
    entries = int(values['entry_sessions'])
    check(len(future) >= entries and future[entries-1] <= endpoint, 'entry window unavailable')
    if profile == 'swing':
        review = future[0]
    else:
        day = anchor.date()
        target = day+timedelta(days=6-day.weekday()) if profile == 'short_term' else day.replace(day=month_calendar.monthrange(day.year,day.month)[1])
        check(at(closes[-1]).date() >= target, 'review calendar unavailable')
        candidates = [s for s in future if at(s).date() <= target]
        if not candidates:
            if profile == 'short_term':
                target += timedelta(days=7)
            else:
                next_month = (target.replace(day=28)+timedelta(days=4)).replace(day=1)
                target = next_month.replace(day=month_calendar.monthrange(next_month.year,next_month.month)[1])
            check(at(closes[-1]).date() >= target, 'next review calendar unavailable')
            candidates = [s for s in future if at(s).date() <= target]
        check(bool(candidates), 'review session unavailable')
        review = candidates[-1]
    lo,hi,units,cadence = {'swing':(2,10,'trading_sessions','each_session'),
        'short_term':(1,3,'calendar_months','weekly'),'long_term':(1,5,'calendar_years','monthly')}[profile]
    return Horizon(schema_version='2.0.0',profile=profile,minimum=lo,maximum=hi,units=units,duration=duration,
        review_cadence=cadence,anchor_at=cutoff,holding_end_at=endpoint,next_review_at=min(review,endpoint),
        entry_expires_at=future[entries-1],calendar_ref=Ref(id='exchange-calendar',version=calendar.version,
            content_hash=digest(json.loads(canonical(asdict(calendar))))))


def legacy_swing(dataset, instrument_id, cutoff, *, code_version, generated_at=None):
    """Compatibility registration: dispatch unchanged v1 behavior, including sizing."""
    return legacy_analyze(dataset,instrument_id,cutoff,code_version=code_version,generated_at=generated_at)


LEGACY_REGISTRATION = MappingProxyType(dict(id='ema-volume-breakout',version=STRATEGY_VERSION,
    formula='EMA10>EMA30;close>prior20high;relative_volume20>=1.5;ATR14',
    entry_tick='0.01',stop_atr_multiple='2',target_r_multiple='2',entry_cap_multiplier='1.01',
    entry_sessions=2,holding_sessions=3,forecast_sessions=5,synthetic_only=True))
LEGACY_REGISTRATION_HASH = digest(dict(LEGACY_REGISTRATION))


def assess(registry, reference, *, profile, instrument_id, cutoff, mode, calendar, bars,
           statements=(), coverage=(), sector='non_financial', eligible=None, risk_prohibited=None):
    """Return a technical-only research assessment; admission always remains blocked.

    Inputs must originate at the rights-gated snapshot boundary. This pure engine
    independently checks clocks, identity, period compatibility and numeric data.
    """
    check(profile in SUPPORTED and mode in ('synthetic','live_paper','historical_reconstructed'), 'profile/mode')
    check(eligible is None or type(eligible) is bool, 'strict eligibility flag')
    check(risk_prohibited is None or type(risk_prohibited) is bool, 'strict instrument-risk flag')
    at(cutoff)
    with localcontext(Context(prec=34)) as context:
        context.prec = 34
        context.rounding = 'ROUND_HALF_EVEN'
        return _assess(registry,reference,profile,instrument_id,cutoff,mode,calendar,bars,
                       statements,coverage,sector,eligible,risk_prohibited)


def _assess(registry, reference, profile, instrument, cutoff, mode, calendar, bars,
            statements, coverage, sector, eligible, risk_prohibited):
    policy = registry.get(reference)
    missing, adverse, metrics, calculations, inputs = [], [], {}, [], []
    horizon = valuation = forecast_end = None
    entry_terms = {}
    values = {}
    conditions_met = False
    known = at(cutoff)
    if policy is None or policy.profile != profile or policy.status == 'unconfigured' or at(policy.effective_at) > known:
        missing.append('policy_not_configured')
    elif mode != 'synthetic' and policy.status != 'approved':
        missing.append('policy_not_configured')
    else:
        values = {p.name:D(p.value) for p in policy.parameters if p.value is not None}
        if len(values) != len(SUPPORTED[profile]):
            missing.append('policy_not_configured')
    for row in coverage:
        row = CoverageCheck.model_validate_json(row.model_dump_json())
        if row.evidence.instrument_id == instrument and available(row.evidence,cutoff,mode) and row.adverse:
            adverse.append('verified_adverse:'+row.requirement)
    if eligible is None or risk_prohibited is None:
        missing.append('eligibility_or_instrument_risk_unavailable')
    if eligible is False:
        adverse.append('instrument_ineligible')
    if risk_prohibited is True:
        adverse.append('instrument_risk_prohibited')

    def calc(name, value, formula, source_ids):
        metrics[name] = wire_number(value)
        record = dict(name=name,value=wire_number(value),formula=formula,formula_version=FORMULA_VERSION,
                      input_ids=sorted(source_ids), unavailable_reason='undefined_denominator_or_missing' if value is None else None)
        record['calculation_id'] = digest(record)
        calculations.append(record)
        return value

    def ratio(name, numerator, denominator, formula, source_ids):
        return calc(name, None if numerator is None or denominator is None or denominator <= 0 else numerator/denominator,formula,source_ids)

    if values and 'policy_not_configured' not in missing:
        try:
            check(calendar.provenance.availability_basis == {'synthetic':'fictional_fixture','live_paper':'observed_live','historical_reconstructed':'verified_archive'}[mode], 'calendar mode')
            check(calendar.provenance.eligible(known.replace(tzinfo=timezone.utc),live=mode=='live_paper'), 'calendar availability')
            horizon = horizon_for(profile,values,calendar,cutoff)
        except (ValueError,IndexError):
            missing.append('calendar_horizon_unavailable')
        required = {'actions','material_events','filings'} | ({'governance','business'} if profile=='long_term' else set())
        checks = {}
        for row in coverage:
            row = CoverageCheck.model_validate_json(row.model_dump_json())
            if row.evidence.instrument_id != instrument or not available(row.evidence,cutoff,mode):
                continue
            prior = checks.get(row.requirement)
            if prior and row.evidence.available_at == prior.evidence.available_at and row != prior:
                missing.append('ambiguous_coverage:'+row.requirement)
            if prior is None or row.evidence.available_at > prior.evidence.available_at:
                checks[row.requirement] = row
        for requirement in sorted(required):
            row = checks.get(requirement)
            if row is None or not row.complete or (known-at(row.evidence.available_at)).total_seconds() > int(values['max_evidence_age_days'])*86400:
                missing.append('missing_or_stale:'+requirement)
            if row is not None:
                inputs.append(row.evidence.model_dump())
                if row.adverse:
                    adverse.append('verified_adverse:'+requirement)
        point = known.replace(tzinfo=timezone.utc)
        selected_bars = tuple(b for b in bars if b.instrument_id == instrument and b.ends_at <= point
                              and b.provenance.eligible(point,live=mode=='live_paper')
                              and b.provenance.availability_basis == {'synthetic':'fictional_fixture','live_paper':'observed_live','historical_reconstructed':'verified_archive'}[mode])
        selected_bars = tuple(sorted(selected_bars,key=lambda b:b.ends_at))
        try:
            check(len(selected_bars)>=30,'warmup')
            expected={(s.opens_at,s.closes_at) for s in calendar.through(point)[-30:]}
            actual={(b.starts_at,b.ends_at) for b in selected_bars[-30:]}
            check(expected==actual and len(expected)==30, 'missing sessions')
            check(all(b.volume>0 for b in selected_bars[-30:]),'zero volume')
            check((point-selected_bars[-1].ends_at).total_seconds() <= int(values['max_price_age_days'])*86400,'stale price')
            f = features(selected_bars)
            check(all(x is not None for x in f.values()),'missing feature')
            inputs.extend(json.loads(canonical(asdict(b))) for b in selected_bars)
        except ValueError:
            missing.append('price_features_unavailable')
            f = {}
        if f:
            price = selected_bars[-1].close
            if profile == 'swing':
                if mode != 'synthetic':
                    missing.append('real_swing_instrument_settings_unavailable')
                for name,value in f.items():
                    calc(name,value,'legacy EMA/breakout/ATR v1.0.2',[digest(json.loads(canonical(asdict(b)))) for b in selected_bars])
                conditions_met = f['ema10']>f['ema30'] and price>f['breakout20'] and f['relative_volume20']>=D('1.5')
                # New research assessment preserves baseline geometry but performs no legacy sizing.
                from .strategy import tick
                entry = tick(selected_bars[-1].high+D('.01'),True)
                stop = tick(entry-2*f['atr14'])
                if stop<=D('.05'):
                    missing.append('invalid_stop')
                entry_terms = dict(trigger=wire_number(entry),cap=wire_number(tick(entry*D('1.01'),True)),
                    stop=wire_number(stop),target=wire_number(tick(entry+2*(entry-stop),True)))
                future = [s for s in calendar.sessions if s.closes_at>point]
                forecast_count = int(values['forecast_sessions'])
                if len(future)<forecast_count:
                    missing.append('forecast_calendar_unavailable')
                else:
                    forecast_end = future[forecast_count-1].closes_at.strftime('%Y-%m-%dT%H:%M:%SZ')
            elif sector != 'non_financial':
                missing.append('unsupported_sector_metrics')
            else:
                financial = []
                for statement in statements:
                    statement = Statement.model_validate_json(statement.model_dump_json())
                    if statement.instrument_id == instrument and available(statement.evidence,cutoff,mode) and at(statement.period_end_at)<=known:
                        financial.append(statement)
                # Stable latest restatement per period; equal-clock conflicts fail closed.
                periods = {}
                for statement in sorted(financial,key=lambda s:(s.period_end_at,s.evidence.available_at,s.revision_id)):
                    key=(statement.period_start_at,statement.period_end_at,statement.scope,statement.period_kind)
                    previous=periods.get(key)
                    if previous and previous.evidence.available_at==statement.evidence.available_at and previous!=statement:
                        missing.append('ambiguous_statement_revision')
                    periods[key]=statement
                annual = sorted((s for s in periods.values() if s.period_kind=='annual'),key=lambda s:(s.period_end_at,s.revision_id))
                kind = 'annual' if values['report_months']==12 else 'quarter'
                reports = sorted((s for s in periods.values() if s.period_kind==kind),key=lambda s:(s.period_end_at,s.revision_id))
                if reports:
                    latest = reports[-1]
                    reports = [s for s in reports if (at(s.period_end_at).month,at(s.period_end_at).day)==(at(latest.period_end_at).month,at(latest.period_end_at).day)]
                if len(reports)<2 or not annual:
                    missing.append('comparable_statements_or_annual_valuation_unavailable')
                else:
                    current, prior = reports[-1],reports[-2]
                    valuation_statement = annual[-1]
                    ids=[current.revision_id,prior.revision_id]
                    inputs.extend(s.model_dump() for s in sorted(periods.values(),key=lambda s:(s.period_end_at,s.revision_id)))
                    if current.scope != prior.scope or current.scope != valuation_statement.scope or not 350 <= (at(current.period_end_at)-at(prior.period_end_at)).days <= 380:
                        missing.append('incompatible_statement_periods')
                    if any((known-at(s.period_end_at)).total_seconds()>int(values['max_statement_age_days'])*86400 for s in (current,valuation_statement)):
                        missing.append('stale_financial_data')
                    required_fields = ('revenue','earnings','diluted_shares') + (('operating_cash_flow','capital_expenditure','debt','cash','equity') if profile=='long_term' else ())
                    if any(getattr(current,k) is None for k in required_fields) or prior.revenue is None or prior.earnings is None or valuation_statement.earnings is None or valuation_statement.diluted_shares is None:
                        missing.append('financial_values_unavailable')
                    else:
                        get=lambda s,k:D(getattr(s,k))
                        revenue,earnings=get(current,'revenue'),get(current,'earnings')
                        growth=ratio('revenue_growth',revenue-get(prior,'revenue'),get(prior,'revenue'),'(revenue-prior_revenue)/prior_revenue',ids)
                        earnings_growth=ratio('earnings_growth',earnings-get(prior,'earnings'),get(prior,'earnings'),'(earnings-prior_earnings)/prior_earnings',ids)
                        eps=ratio('eps',get(valuation_statement,'earnings'),get(valuation_statement,'diluted_shares'),'annual_earnings/diluted_shares',[valuation_statement.revision_id])
                        confirmation=ratio('price_confirmation',price,f['sma20'],'close/SMA20',[digest(json.loads(canonical(asdict(b)))) for b in selected_bars[-20:]])
                        if growth is None or earnings_growth is None or eps is None or eps<=0:
                            missing.append('undefined_financial_ratio')
                        else:
                            scenario_values={name:calc(name+'_value',eps*values[name+'_pe'],'annual_EPS * registered_'+name+'_PE',[valuation_statement.revision_id]) for name in ('bear','base','bull')}
                            valuation=Valuation(low=wire_number(scenario_values['bear']),high=wire_number(scenario_values['bull']),currency='INR',valued_at=cutoff,
                                assumptions=[name+'_PE='+wire_number(values[name+'_pe']) for name in ('bear','base','bull')]+['Annual EPS; scenario values are not trading targets'],
                                calculation_ids=[r['calculation_id'] for r in calculations if r['name'].endswith('_value')])
                            ceiling=scenario_values['bear']*(1-values['min_margin_of_safety'])
                            entry_terms=dict(max_price=wire_number(ceiling),minimum_price_confirmation=wire_number(values['min_price_to_sma']))
                            conditions_met = growth>=values['min_revenue_growth'] and earnings_growth>=values['min_earnings_growth'] and confirmation>=values['min_price_to_sma'] and price<=ceiling
                            if profile=='long_term':
                                ocf=get(current,'operating_cash_flow')
                                ocf_margin=ratio('ocf_margin',ocf,revenue,'OCF/revenue',ids)
                                roe=ratio('roe',earnings,get(current,'equity'),'earnings/closing_equity',ids)
                                leverage=ratio('net_debt_to_ocf',get(current,'debt')-get(current,'cash'),ocf,'(debt-cash)/OCF',ids)
                                fcf=calc('free_cash_flow',ocf-get(current,'capital_expenditure'),'OCF-positive_capex',ids)
                                fcf_yield=ratio('fcf_yield',fcf,get(current,'diluted_shares')*price,'FCF/(shares*price)',ids)
                                years=int(values['durability_years'])
                                history=annual[-years:]
                                durability_ok=len(history)==years
                                for a,b in zip(history,history[1:]):
                                    durability_ok &= a.scope==b.scope and 350 <= (at(b.period_end_at)-at(a.period_end_at)).days <= 380
                                if not durability_ok or any(s.operating_cash_flow is None or s.revenue is None or D(s.revenue)<=0 for s in history):
                                    missing.append('durability_history_unavailable')
                                else:
                                    durability=calc('durability_ocf_margin',min(D(s.operating_cash_flow)/D(s.revenue) for s in history),'minimum annual OCF/revenue across registered history',[s.revision_id for s in history])
                                    conditions_met &= durability>=values['min_ocf_margin']
                                if any(x is None for x in (ocf_margin,roe,leverage,fcf_yield)):
                                    missing.append('undefined_quality_ratio')
                                else:
                                    if leverage>values['max_net_debt_to_ocf']:
                                        adverse.append('leverage_limit_exceeded')
                                    conditions_met &= ocf_margin>=values['min_ocf_margin'] and roe>=values['min_roe'] and fcf_yield>=values['min_fcf_yield']
    if horizon is not None:
        future_opens = [s.opens_at for s in calendar.sessions if s.opens_at > known.replace(tzinfo=timezone.utc)]
        if not future_opens:
            missing.append('entry_session_unavailable')
        else:
            entry_terms['earliest_entry_at'] = future_opens[0].strftime('%Y-%m-%dT%H:%M:%SZ')
    action = 'INSUFFICIENT_EVIDENCE' if missing else 'AVOID' if adverse else 'BUY' if conditions_met else 'WATCH'
    reasons = sorted(set(missing if missing else adverse if adverse else []))
    evidence_ids = sorted({r.evidence.evidence_id for r in coverage if r.evidence.instrument_id==instrument and available(r.evidence,cutoff,mode)})
    evidence_ids = sorted(set(evidence_ids) | {r['evidence']['evidence_id'] for r in inputs if 'evidence' in r})
    registered_limits = {k:wire_number(v) for k,v in sorted(values.items()) if k.startswith(('min_','max_'))}
    conditions = None if horizon is None else Conditions(
        entry=[Condition(code='quant_entry_conditions',explanation=json.dumps(entry_terms,sort_keys=True)+'; required quantitative limits: '+json.dumps(registered_limits,sort_keys=True)+'; mandatory coverage must be current; enter only before expiry',evidence_ids=evidence_ids)],
        invalidation=[Condition(code='thesis_invalidated',explanation='Invalidate readiness on violation of '+json.dumps(registered_limits,sort_keys=True)+' or verified adverse evidence, prohibited instrument risk or stale mandatory data; no automatic portfolio action',evidence_ids=evidence_ids)],
        review=[Condition(code=horizon.review_cadence,explanation='Review on pinned cadence and material events; holding endpoint is separate',evidence_ids=evidence_ids)],expires_at=horizon.entry_expires_at)
    result=dict(schema_version='1.0.0',formula_version=FORMULA_VERSION,profile=profile,instrument_id=instrument,mode=mode,
        information_cutoff_at=cutoff,policy_ref=reference.model_dump(),policy_manifest_hash=None if policy is None else digest(policy.model_dump()),
        action=action,reasons=reasons,known_adverse=sorted(set(adverse)),capability='technical_only',
        metrics=metrics,calculations=calculations,valuation=None if valuation is None else valuation.model_dump(),
        horizon=None if horizon is None else horizon.model_dump(),forecast_end_at=forecast_end,
        conditions=None if conditions is None else conditions.model_dump(),entry_terms=entry_terms,
        input_hash=digest(inputs),input_refs=sorted(digest(r) for r in inputs),paper_admission=dict(status='blocked',quantity=None,reason='paper_admission_not_evaluated'))
    result['assessment_id']=digest(result)
    return result


def entry_conditions_met(assessment, attempted_at, price):
    """Research price/time gate only; never grants paper admission or submits orders."""
    check(isinstance(price,D) and price.is_finite() and price>0, 'positive Decimal price')
    attempt=at(attempted_at)
    if assessment['action']!='BUY' or assessment['horizon'] is None:
        return False
    terms=assessment['entry_terms']
    if not at(terms['earliest_entry_at']) <= attempt < at(assessment['horizon']['entry_expires_at']):
        return False
    if assessment['profile']=='swing':
        return D(terms['trigger']) <= price <= D(terms['cap'])
    return price <= D(terms['max_price'])
