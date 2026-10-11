"""Daily OHLC replay. Unknown intrabar order stays ambiguous, never optimized."""
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal as D
from .dataset import Dataset
from .data import aware
from .strategy import stamp


def dt(value): return datetime.fromisoformat(value.replace('Z','+00:00'))


@dataclass(frozen=True)
class Costs:
    version: str = 'SYN-daily-costs-v1'
    effective_from: datetime = datetime(2020,1,1,tzinfo=timezone.utc)
    effective_to: datetime = datetime(2030,1,1,tzinfo=timezone.utc)
    brokerage_per_side: D = D('1')
    fees_per_share_side: D = D('.10')
    adverse_slippage: D = D('.05')

    def __post_init__(self):
        if aware(self.effective_from)>=aware(self.effective_to): raise ValueError('invalid cost dates')
        if any(not v.is_finite() or v<0 for v in (self.brokerage_per_side,self.fees_per_share_side,self.adverse_slippage)):
            raise ValueError('invalid costs')

    def fee(self,q): return self.brokerage_per_side+self.fees_per_share_side*q


def simulate(analysis: dict, dataset: Dataset, evaluated_at: datetime, costs: Costs=Costs()) -> dict:
    r=analysis['recommendation']; aware(evaluated_at)
    cutoff=dt(r['information_cutoff_at'])
    if evaluated_at<cutoff: raise ValueError('evaluation predates signal')
    if r['versions']['dataset']!=dataset.version: raise ValueError('frozen dataset mismatch')
    out={'schema_version':'1.1.0','synthetic':True,'recommendation_id':r['recommendation_id'],
         'evaluated_at':stamp(evaluated_at),'evaluator_version':'daily-replay-v1',
         'observation_dataset':dataset.version,'forecast':{'status':'not_applicable','direction_matches':None},
         'trade':{'status':'not_applicable','reason':'non_actionable','fills':[], 'gross_pnl':None,
                  'estimated_costs':D(0),'net_pnl':None,'sensitivity_net_pnl':None},
         'equity_curve':[],'exclusions':[]}
    if r['action']!='BUY': return out
    x=r['execution']; q=x['quantity']; t=out['trade']; f=out['forecast']
    if x['assumptions_version']!=costs.version: raise ValueError('cost version mismatch')
    start=dt(r['earliest_executable_entry_at']); expiry=dt(x['entry_expires_at'])
    endpoint=dt(r['forecast']['end_at'])
    sessions=[s for s in dataset.calendar.sessions if s.opens_at>=start and s.closes_at<=endpoint]
    all_bars={c.starts_at:c for c in dataset.asof(r['instrument']['instrument_id'],evaluated_at)}
    if any(a.instrument_id==r['instrument']['instrument_id'] and start<=a.effective_at<=endpoint
           and a.provenance.eligible(evaluated_at) for a in dataset.actions):
        t.update(status='invalid_data',reason='corporate_action_execution_unsupported')
        f.update(status='invalid_data'); out['exclusions'].append(t['reason']); return out
    endpoint_bar=next((c for c in all_bars.values() if c.ends_at==endpoint),None)
    if evaluated_at<endpoint: f['status']='pending'
    elif endpoint_bar is None: f['status']='invalid_data'
    else:
        ref=D(r['forecast']['reference_price']); price=endpoint_bar.close
        actual='up' if price>ref else 'down' if price<ref else 'flat'
        f.update(status='matured',direction_matches=actual==r['forecast']['direction'],reference_price=ref,
                 observed_price=price,realized_direction=actual,price_return_pct=(price/ref-1)*100)
    trigger=D(x['entry']['trigger_price']); stop=D(x['stop']['price']); target=D(x['targets'][0]['price'])
    cap=D(analysis['sizing']['entry_cap']); entry=None; held=0; cash=D('100000')
    out['equity_curve']=[{'at':stamp(cutoff),'cash':cash,'positions':[],'external_flow':D(0)}]
    t.update(status='pending',reason='awaiting_entry_window')
    def fill(side,c,price,role,at_open=False):
        return {'side':side,'interval_start':stamp(c.starts_at),'interval_end':stamp(c.ends_at),
                'timing':'open' if at_open else 'within_session_unknown','price':price,'quantity':q,'role':role}
    def finish(c,price,reason,at_open=False):
        nonlocal cash
        fee=costs.fee(q); cash+=q*price-fee
        t['fills'].append(fill('SELL',c,price,'exit',at_open))
        gross=(price-entry)*q
        t.update(status='closed',reason=reason,gross_pnl=gross,estimated_costs=2*fee,net_pnl=gross-2*fee)
    for s in sessions:
        if s.closes_at>evaluated_at: break
        c=all_bars.get(s.opens_at)
        if c is None or c.ends_at!=s.closes_at or c.volume<=0:
            t.update(status='invalid_data',reason='missing_or_invalid_session'); out['equity_curve']=[]; break
        if not costs.effective_from<=s.opens_at<costs.effective_to:
            t.update(status='invalid_data',reason='cost_schedule_unavailable'); out['equity_curve']=[]; break
        if entry is None and s.opens_at>=expiry:
            t.update(status='no_entry',reason='entry_expired'); break
        at_open=False
        if entry is None:
            if c.open<=stop:
                t.update(status='cancelled',reason='invalidated_before_entry'); break
            if c.high<trigger: continue
            at_open=c.open>=trigger
            price=max(c.open,trigger)+costs.adverse_slippage
            if price>cap or price>=target:
                t.update(status='cancelled',reason='gap_above_entry_cap_or_target'); break
            if q>D(c.volume)*D('.01') or q*price+costs.fee(q)>cash:
                t.update(status='invalid_data',reason='liquidity_or_cash_limit'); break
            entry=price; cash-=q*entry+costs.fee(q)
            t['fills'].append(fill('BUY',c,entry,'entry',at_open)); t['estimated_costs']=costs.fee(q)
            t.update(status='open',reason='holding')
            # An intraday entry and stop may have happened in either order.
            if not at_open and c.low<=stop:
                low=(stop-costs.adverse_slippage-entry)*q-2*costs.fee(q)
                high=(target-entry)*q-2*costs.fee(q) if c.high>=target else None
                t.update(status='ambiguous',reason='entry_stop_order_unknown',sensitivity_net_pnl={'stop_path':low,'target_path':high,'no_entry_path':True})
                out['equity_curve']=[]; break
        held+=1
        if not at_open and held>1 and c.open<=stop:
            finish(c,max(D('.01'),c.open-costs.adverse_slippage),'gap_stop',True)
        elif held>1 and c.open>=target:
            finish(c,target,'target',True)
        elif c.low<=stop and c.high>=target:
            t.update(status='ambiguous',reason='stop_target_order_unknown',sensitivity_net_pnl={
                'stop_path':(stop-costs.adverse_slippage-entry)*q-2*costs.fee(q),
                'target_path':(target-entry)*q-2*costs.fee(q)})
            out['equity_curve']=[]; break
        elif c.low<=stop: finish(c,max(D('.01'),stop-costs.adverse_slippage),'stop')
        elif c.high>=target: finish(c,target,'target')
        elif held>=x['max_holding_sessions']: finish(c,max(D('.01'),c.close-costs.adverse_slippage),'maximum_holding_expired')
        out['equity_curve'].append({'at':stamp(c.ends_at),'cash':cash,'positions':[] if t['status']=='closed' else [{'quantity':q,'mark':c.close}], 'external_flow':D(0)})
        if t['status']=='closed': break
    if entry is None and t['status']=='pending' and evaluated_at>=expiry:
        t.update(status='no_entry',reason='entry_expired')
    if t['status'] in ('invalid_data','ambiguous'):
        out['exclusions'].append(t['reason']); out['equity_curve']=[]
    return out
