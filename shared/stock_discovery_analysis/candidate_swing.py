"""STK-094 / D3-05 + D3-09: current stored-price research order, not signals."""
from decimal import Decimal, InvalidOperation
from .candidate_research import analyze
from .publication_store import now


def review(research):
    result=dict(status='unavailable',rank=None,price_checks_met=None,
        checks=dict(ema_trend=None,price_breakout=None,relative_volume=None),
        reasons=list(research.get('reasons',[])),actionable=False,
        strategy_status='incomplete_volume_basis_unverified')
    technical=research.get('technical',{})
    if research.get('status')!='completed' or technical.get('status')!='AVAILABLE_DESCRIPTIVE_ONLY':
        return result
    if technical.get('freshness',{}).get('status')!='current':
        return {**result,'reasons':['current_price_session_required']}
    try:
        metrics=technical['metrics']
        close=Decimal(research['market_data']['latest_close'])
        fast,slow,high=(Decimal(metrics[k]) for k in ('ema10','ema30','breakout20'))
        if any(not v.is_finite() or v<=0 for v in (close,fast,slow,high)):
            raise ValueError('invalid_prices')
    except (KeyError,TypeError,ValueError,InvalidOperation):
        return {**result,'reasons':['price_indicators_unavailable']}
    checks=dict(ema_trend=fast>slow,price_breakout=close>high,relative_volume=None)
    return {**result,'status':'available_descriptive_only','checks':checks,
            'price_checks_met':int(checks['ema_trend'])+int(checks['price_breakout']),
            'reasons':['volume_basis_unverified','not_a_complete_strategy_signal']}


def page(conn, config, candidates, *, clock=now):
    # Re-evaluate at one current clock; cached worker results can have aged.
    evaluated_at=clock()
    for row in candidates['rows']:
        research=analyze(conn,config,row['symbol'],row['session_date'],clock=lambda:evaluated_at)
        row['research']=research
        row['research_status']=research['status']
        row['swing_review']=review(research)
    candidates['rows'].sort(key=lambda row:(
        -(row['swing_review']['price_checks_met'] if row['swing_review']['price_checks_met'] is not None else -1),
        row['symbol'],row['candidate_id']))
    scores=sorted({r['swing_review']['price_checks_met'] for r in candidates['rows']
                   if r['swing_review']['price_checks_met'] is not None},reverse=True)
    for row in candidates['rows']:
        score=row['swing_review']['price_checks_met']
        if score is not None:row['swing_review']['rank']=scores.index(score)+1
    return {**candidates,'evaluated_at':evaluated_at,'ranking_scope':'displayed_page_only',
            'ranking_basis':'current_price_checks_met_equal_scores_share_rank',
            'provider_requests':0,'model_requests':0,'actionable':False}
