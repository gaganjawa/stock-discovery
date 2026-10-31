import {useRef,useState,useEffect,type FormEvent} from 'react'
type Result={instrument_id:string;status:'BUY'|'WAIT'|'INSUFFICIENT_EVIDENCE';analysis_cutoff_at:string;reasons:string[];indicators:Record<string,string>;levels:Record<string,string>|null;hypothetical_sizing:{quantity:number;planned_loss:string;entry_cash:string;scenario_only:boolean}|null;evidence_revisions:string[];formula_version?:string;strategy_version?:string;policy_version?:string;analysis_id:string|null}
export function RealSwing({listing,onUnauthorized}:{listing:string;onUnauthorized:()=>void}){
 const [cutoff,setCutoff]=useState(''),[data,setData]=useState<Result|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false)
 const active=useRef<AbortController|null>(null)
 useEffect(()=>()=>active.current?.abort(),[])
 async function analyze(e:FormEvent){
  e.preventDefault();active.current?.abort();const c=new AbortController();active.current=c
  setData(null);setError('');setBusy(true)
  const params=new URLSearchParams({analysis:'swing'});if(cutoff)params.set('cutoff_at',cutoff)
  try{
   const r=await fetch('/v1/real-research/companies/'+encodeURIComponent(listing)+'?'+params,{signal:c.signal,cache:'no-store'})
   if(r.status===401){onUnauthorized();throw Error('Sign in to analyze stored evidence.')}
   if(!r.ok)throw Error(r.status===403?'Source permission denied.':'Swing inputs are unavailable. Check source configuration and cutoff.')
   const result:Result=await r.json();if(!c.signal.aborted)setData(result)
  }catch(e){if(!c.signal.aborted)setError(e instanceof Error?e.message:'Swing analysis is unavailable.')}
  finally{if(!c.signal.aborted)setBusy(false)}
 }
 return <section className="panel" aria-label="Technical swing research"><h3>Technical swing research</h3>
 <p>Analyzes permitted stored evidence. BUY is a research candidate; publication, paper admission and trading remain blocked.</p>
 <form onSubmit={analyze}><label>Analysis cutoff (UTC, optional)<input value={cutoff} onChange={e=>{active.current?.abort();setBusy(false);setData(null);setError('');setCutoff(e.target.value)}} placeholder="2026-10-31T10:00:00Z"/></label><button disabled={busy}>{busy?'Analyzing…':'Analyze stored swing evidence'}</button></form>
 <p>Leave blank for current analysis. An earlier cutoff does not establish a frozen historical replay or reveal future outcomes.</p>
 {error&&<p role="alert">{error}</p>}
 {data&&<><h4>{data.status.replaceAll('_',' ')}</h4><p>{data.instrument_id} · cutoff {data.analysis_cutoff_at} · Research only</p><ul>{data.reasons.map(r=><li key={r}>{r.replaceAll('_',' ')}</li>)}</ul>
 <dl>{Object.entries(data.indicators).map(([k,v])=><div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>
 {data.levels&&<><h4>Hypothetical price levels</h4><dl>{Object.entries(data.levels).map(([k,v])=><div key={k}><dt>{k.replaceAll('_',' ')}</dt><dd>{v}</dd></div>)}</dl></>}
 {data.hypothetical_sizing&&<p>Scenario quantity: {data.hypothetical_sizing.quantity}. Planned loss including configured fees and stop slippage: {data.hypothetical_sizing.planned_loss} INR. Entry cash: {data.hypothetical_sizing.entry_cash} INR. Hypothetical sizing is not account or execution authorization.</p>}
 <details><summary>Evidence and versions</summary><p>Formula: {data.formula_version??'Unavailable'} · Strategy: {data.strategy_version??'Unavailable'} · Policy: {data.policy_version??'Unavailable'}</p><p>Analysis: {data.analysis_id??'Unavailable'}</p><ul>{data.evidence_revisions.map(r=><li key={r}>{r}</li>)}</ul></details>
 </>}
 </section>
}
