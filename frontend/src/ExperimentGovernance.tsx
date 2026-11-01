import {useEffect,useMemo,useState} from 'react'
import {RegisteredFoldResults} from './RegisteredFoldResults'

type Summary={experiment_id:string;horizon:string;comparison:string;registered_at:string}
type Result={status:string;error_code?:string;evidence_class?:string;arms?:Record<string,{decisions:number;resolved_trades:number;missing_outcomes:number;research_failed:number;no_picks:boolean;win_rate:string|null;portfolio_return:string|null;benchmark_reason:string;forecast_quality:{matured:number;provisional:number}}>}
type Detail={manifest:{experiment_id:string;hypothesis:string;historical_llm_contamination:string;stopping_rule:string};promotion:{eligible:boolean;reasons:string[]};history:{sequence:number;kind:string;at:string}[];trials:{trial_id:string;request:{split:string};result:Result|null}[]}
const label=(s:string)=>s.replaceAll('_',' ')
export function ExperimentGovernance({onUnauthorized,initialExperimentId}:{onUnauthorized:()=>void;initialExperimentId?:string}){
 const [items,setItems]=useState<Summary[]>([]),[detail,setDetail]=useState<Detail|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false)
 async function get(path:string){const r=await fetch('/v1/experiments'+path);if(!r.ok){setItems([]);setDetail(null);if(r.status===401)onUnauthorized();throw new Error(r.status===403?'Source permission denied. Stored results are hidden.':'Experiment records are unavailable.')}return r.json()}
 async function load(){setBusy(true);setError('');setDetail(null);try{setItems((await get('')).experiments)}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 async function inspect(id:string){setBusy(true);setDetail(null);setError('');try{setDetail(await get('/'+encodeURIComponent(id)))}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 useEffect(()=>{void load()},[])
 const foldItems=useMemo(()=>initialExperimentId&&!items.some(e=>e.experiment_id===initialExperimentId)?[{experiment_id:initialExperimentId},...items]:items,[items,initialExperimentId])
 return <section className="panel" aria-label="Experiment governance">
  <h2>Experiment governance</h2><p>Compare quantitative research, fixed RAG and bounded investigation using frozen inputs and recorded outcomes. Historical AI research remains exploratory.</p>
  <p className="notice">Strategy promotion blocked. Policy thresholds and independent prospective evidence are required. Q+ML is disabled.</p>
  <button disabled={busy} onClick={()=>void load()}>Refresh experiments</button>
  {initialExperimentId&&<p>Selected research registration: {initialExperimentId}. Results require a fresh authorized read; no trial will be evaluated.</p>}
  <RegisteredFoldResults experiments={foldItems} initialExperimentId={initialExperimentId} onUnauthorized={onUnauthorized} onRestricted={()=>{setDetail(null);setItems([]);setError('Source permission denied. Stored results are hidden.')}}/>
  {error&&<p role="alert">{error}</p>}
  {!items.length&&!error&&<p>No registered experiments. Preregister the hypothesis, splits, versions and stopping rules through the authenticated experiment API before evaluating outcomes.</p>}
  {items.map(item=><p key={item.experiment_id}><button disabled={busy} onClick={()=>void inspect(item.experiment_id)}>{item.experiment_id}</button> · {label(item.horizon)} · {label(item.comparison)} · {new Date(item.registered_at).toLocaleString()}</p>)}
  {detail&&<section aria-label="Experiment details"><h3>{detail.manifest.hypothesis}</h3><p>Stopping rule: {detail.manifest.stopping_rule}</p><p>Model knowledge: {label(detail.manifest.historical_llm_contamination)}</p>
   <details><summary>Promotion blockers</summary><ul>{detail.promotion.reasons.map(r=><li key={r}>{label(r)}</li>)}</ul></details>
   {detail.trials.map(t=><section key={t.trial_id} aria-label="Registered trial"><h4>{t.trial_id} · {t.request.split}</h4><p>{label(t.result?.status??'registered; not evaluated')} · {label(t.result?.evidence_class??'evidence not established')}</p>
    {t.result?.error_code&&<p>Validation failure: {label(t.result.error_code)}</p>}
    {t.result?.arms&&<div className="table-wrap"><table><caption>Separate decisions, trade outcomes and forecast maturity</caption><thead><tr><th>Arm</th><th>Decisions</th><th>Resolved trades</th><th>Missing outcomes</th><th>Research failures</th><th>Mature forecasts</th><th>Provisional forecasts</th><th>Trade win rate</th><th>Portfolio return</th></tr></thead><tbody>{Object.entries(t.result.arms).map(([arm,m])=><tr key={arm}><td>{label(arm)}{m.no_picks?' · no picks':''}</td><td>{m.decisions}</td><td>{m.resolved_trades}</td><td>{m.missing_outcomes}</td><td>{m.research_failed}</td><td>{m.forecast_quality.matured}</td><td>{m.forecast_quality.provisional}</td><td>{m.win_rate??'Unavailable'}</td><td>{m.portfolio_return??'Unavailable'}</td></tr>)}</tbody></table><p>Missing benchmarks and immature outcomes do not establish an investment advantage.</p></div>}
   </section>)}
   <details><summary>Immutable trial history</summary>{detail.history.map(h=><p key={h.sequence}>{new Date(h.at).toLocaleString()} · {label(h.kind)}</p>)}</details>
  </section>}
 </section>
}
