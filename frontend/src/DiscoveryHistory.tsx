import {useEffect,useRef,useState} from 'react'

type Saved={recommendation_id:string;cutoff_at:string;generated_at:string;action:string;selected:boolean}
type Recorded={portfolio_id:string;sequence:number;event_hash:string;observed_at:string;available_at:string;url:string}
type History={recommendation_id:string;cutoff_at:string;records:Saved[];next_cursor:string|null;outcomes:Recorded[];evaluations:{experiment_id:string;trial_id:string;phase:string}[];limitations:string[]}
type Outcome={portfolio_id:string;sequence:number;event_hash:string;observation_cutoff_at:string;knowledge_cutoff_at:string;outcome:{status:string;reason:string;original_decision:string;realized_pnl:string;fees:string;slippage:string;forecast:{status:string;return:string|null}};history:{sequence:number;at:string;kind:string;event_hash:string}[];limitations:string[]}
const label=(v:string)=>v.replaceAll('_',' ')

export function DiscoveryHistory({recommendationId,onOpen,onEvaluation,onDenied,onUnauthorized}:{recommendationId:string;onOpen:(id:string)=>Promise<void>;onEvaluation:(id:string)=>void;onDenied:()=>void;onUnauthorized:()=>void}){
 const [data,setData]=useState<History|null>(null),[outcome,setOutcome]=useState<Outcome|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('')
 const active=useRef<AbortController|null>(null)
 useEffect(()=>{setData(null);setOutcome(null);setError('');setBusy(false);return()=>active.current?.abort()},[recommendationId])
 async function get(path:string,c:AbortController){const r=await fetch(path,{signal:c.signal,cache:'no-store'});c.signal.throwIfAborted()
  if(!r.ok){setData(null);setOutcome(null);if(r.status===401)onUnauthorized();if(r.status===403)onDenied();throw Error(r.status===403?'Saved evidence is restricted. All related content is hidden.':'Saved evidence is missing or inconsistent. No replacement was generated.')}
  const value=await r.json();c.signal.throwIfAborted();return value
 }
 async function work(fn:(c:AbortController)=>Promise<void>){active.current?.abort();const c=new AbortController();active.current=c;setBusy(true);setError('');setOutcome(null)
  try{await fn(c)}catch(e){if(!c.signal.aborted)setError(e instanceof Error?e.message:'Saved evidence is unavailable.')}
  finally{if(!c.signal.aborted)setBusy(false)}
 }
 async function load(c:AbortController,before?:string){setData(null);const q=new URLSearchParams();if(before)q.set('before',before);setData(await get('/v1/recommendations/'+encodeURIComponent(recommendationId)+'/history?'+q,c))}
 return <section className="panel" aria-label="Discovery saved evidence"><h4>Saved evidence and recorded outcomes</h4><p>Open the original frozen record. Later outcomes stay hidden until explicitly revealed. No new inference, evaluation or paper admission is performed.</p>
 <button disabled={busy} onClick={()=>void work(c=>load(c))}>Open saved historical evidence</button>
 {error&&<p role="alert">{error}</p>}
 {data&&<><p>Selected frozen cutoff: {data.cutoff_at}. Historical evidence is not a current market signal.</p>
 <h5>Publication history</h5>{!data.records.length&&<p>No related publication records.</p>}{data.records.map(r=><p key={r.recommendation_id}>{r.cutoff_at} · {label(r.action)} · recorded {r.generated_at}<br/>{r.selected?'Selected frozen recommendation':<button disabled={busy} onClick={()=>void work(async()=>onOpen(r.recommendation_id))}>Inspect frozen recommendation {r.recommendation_id}</button>}</p>)}
 {data.next_cursor&&<button disabled={busy} onClick={()=>void work(c=>load(c,data.next_cursor!))}>Older publication evidence</button>}
 <h5>Recorded outcome references</h5>{!data.outcomes.length&&<p>Outcome unavailable: no recorded ledger relates to this recommendation. No history will be invented.</p>}
 {data.outcomes.map(o=><p key={o.portfolio_id}>Portfolio {o.portfolio_id} · immutable ledger #{o.sequence}<br/>Observed through {o.observed_at} · known by {o.available_at}<br/><button disabled={busy} onClick={()=>void work(async c=>setOutcome(await get(o.url,c)))}>Reveal recorded outcome {o.portfolio_id}</button></p>)}
 {outcome&&<section aria-label="Recorded discovery outcome"><h5>Subsequent recorded outcome</h5><p>Original decision: {outcome.outcome.original_decision} · {label(outcome.outcome.status)} · {label(outcome.outcome.reason)}</p><p>Observation cutoff {outcome.observation_cutoff_at} · knowledge cutoff {outcome.knowledge_cutoff_at}<br/>Pinned ledger #{outcome.sequence} · {outcome.event_hash}</p><p>Realized P&amp;L {outcome.outcome.realized_pnl} INR · fees {outcome.outcome.fees} · slippage {outcome.outcome.slippage}<br/>Forecast: {label(outcome.outcome.forecast.status)} · endpoint return {outcome.outcome.forecast.return??'Unavailable'}. Forecasts and trade outcomes are separate.</p><details><summary>Recorded recommendation history</summary>{outcome.history.map(h=><p key={h.sequence}>#{h.sequence} · {h.at} · {label(h.kind)}<br/>{h.event_hash}</p>)}</details>{outcome.limitations.map(v=><p key={v}>{v}</p>)}</section>}
 <h5>Registered evaluation</h5>{!data.evaluations.length&&<p>Evaluation unavailable: no registered trial references this recommendation.</p>}{data.evaluations.map(e=><p key={e.trial_id}>{e.trial_id} · {label(e.phase)} · registration reference only <button disabled={busy} onClick={()=>onEvaluation(e.experiment_id)}>View registered evaluation {e.experiment_id}</button></p>)}
 <p>Legacy Replay unavailable: no explicit dataset relationship. SYN-D309 and legacy Replay fixtures remain separate.</p>{data.limitations.map(v=><p key={v}>{v}</p>)}
 </>}
 </section>
}
