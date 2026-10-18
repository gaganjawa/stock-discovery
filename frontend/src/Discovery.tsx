import { useEffect, useState } from 'react'

type Rec = {recommendation_id:string;instrument:{symbol:string;issuer_id:string};horizon:{profile:string;duration:number;units:string;holding_end_at:string;entry_expires_at:string;next_review_at:string};action:string;information_cutoff_at:string;generated_at:string;cohort:{arm:string};rationale:{summary:string};risk_context:{eligibility:string;binding_constraints:string[]};paper_admission:{status:string;reason:string;quantity:null};evidence_quality:{uncertainty:string[];missing_required:string[];contradiction_ids:string[]};research_status:string;action_reason_codes:string[];conditions:{entry:{explanation:string}[];invalidation:{explanation:string}[]};valuation:null|{low:string;high:string;assumptions:string[]};execution:null|{entry_price:string;stop_price:string;target_price:string|null};versions:Record<string,string|null>}
type Run={run_id:string;status:string;stage:string;error_code:string|null}
type Page={status:string;batch_id:string|null;recommendations:Rec[];coverage:Record<string,number>|null;latest_run:Run|null;information_cutoff_at?:string;published_at?:string;source_issues?:string[];next_cursor:string|null}
type Citation={evidence_id:string;revision_id:string;attribution:string;source_url:string;locator:string;excerpt:string|null}
type Detail={recommendation:Rec;quantitative:{metrics:Record<string,string|null>;known_adverse:string[]};research:null|{assessment?:{claims:{text:string}[]};validator?:Record<string,string>;error_code?:string};citations:Citation[];publication_status:string;permissions:Record<string,{grant_id:string;version:string;status:string}>}
const horizons=[['swing','Swing','2–10 trading days'],['short_term','Short-term','1–3 months'],['long_term','Long-term','1–5 years']]
const modes=[['quant','Quantitative only'],['quant_rag','Quantitative + RAG'],['quant_agent','Quantitative + agent']]
const label=(s:string)=>s.replaceAll('_',' ')
const number=(s:string|null)=>s===null?'Unavailable':Number(s).toLocaleString('en-IN',{maximumFractionDigits:4})
const time=(s?:string)=>s?new Date(s).toLocaleString('en-IN',{timeZone:'Asia/Kolkata'})+' IST':'Not yet available'

export function Discovery({onUnauthorized}:{onUnauthorized:()=>void}) {
 const [horizon,setHorizon]=useState('swing'),[cohort,setCohort]=useState('quant')
 const [data,setData]=useState<Page|null>(null),[detail,setDetail]=useState<Detail|null>(null),[comparisons,setComparisons]=useState<Rec[]>([])
 const [source,setSource]=useState<{document:{title:string;attribution:string};chunks:{text:string}[]}|null>(null)
 const [error,setError]=useState(''),[busy,setBusy]=useState(false),[run,setRun]=useState<Run|null>(null),[requestKey,setRequestKey]=useState<string|null>(null)
 async function api(path:string,body?:unknown,key?:string){
  const r=await fetch('/v1'+path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json','Idempotency-Key':key!}:{},body:body?JSON.stringify(body):undefined})
  if(!r.ok){if(r.status===401)onUnauthorized();if(r.status===403){setData(null);setDetail(null);setComparisons([]);setSource(null)}const e=await r.json().catch(()=>({}));throw new Error(e.detail?.message??'Discovery is unavailable. Please retry.')}
  return r.json()
 }
 async function load(){const p:Page=await api(`/discovery?horizon=${horizon}&cohort=${cohort}`);setData(p);setRun(p.latest_run)}
 useEffect(()=>{let active=true;setData(null);setDetail(null);setComparisons([]);setSource(null);setError('');setRequestKey(null)
  api(`/discovery?horizon=${horizon}&cohort=${cohort}`).then(p=>{if(active){setData(p);setRun(p.latest_run)}}).catch(e=>{if(active)setError(e.message)})
  return()=>{active=false}
 },[horizon,cohort])
 useEffect(()=>{if(!run||!['queued','running'].includes(run.status))return
  const timer=setInterval(()=>{api('/runs/'+run.run_id).then((r:Run)=>{setRun(r);if(!['queued','running'].includes(r.status))load().catch(e=>setError(e.message))}).catch(e=>setError(e.message))},1500)
  return()=>clearInterval(timer)
 },[run?.run_id,run?.status,horizon,cohort])
 async function work(fn:()=>Promise<void>){setBusy(true);setError('');try{await fn()}catch(e){setError(e instanceof Error?e.message:'Request failed')}finally{setBusy(false)}}
 async function start(){const key=requestKey??crypto.randomUUID();setRequestKey(key);const response=await api('/discovery-runs',{horizon},key);setRun({run_id:response.run_id,status:'queued',stage:'queued',error_code:null});setRequestKey(null)}
 async function inspect(r:Rec){setDetail(null);setComparisons([]);setSource(null);const d=await api('/recommendations/'+r.recommendation_id);setDetail(d);setComparisons((await api('/recommendations/'+r.recommendation_id+'/comparisons')).recommendations)}
 const pending=!!run&&['queued','running'].includes(run.status)
 return <section aria-label="Three-horizon discovery" className="discovery">
  <div className="discovery-heading"><div><p className="eyebrow">AUTOMATIC INGESTION · LOCAL MOCK RESEARCH</p><h2>Three-horizon discovery</h2><p>Five fictional companies. Published decisions are immutable and cannot place orders.</p></div><span className="badge">MOCK / SHADOW / NON-ACTIONABLE</span></div>
  <div role="tablist" aria-label="Investment horizon" className="horizon-tabs">{horizons.map(([id,name,range])=><button key={id} role="tab" aria-selected={horizon===id} disabled={busy||pending} onClick={()=>setHorizon(id)}><strong>{name}</strong><small>{range}</small></button>)}</div>
  <div className="controls"><label>Research mode<select aria-label="Discovery research mode" value={cohort} disabled={busy} onChange={e=>setCohort(e.target.value)}>{modes.map(([id,name])=><option key={id} value={id}>{name}</option>)}</select></label><button className="primary" disabled={busy||pending} onClick={()=>work(start)}>{pending?'Research in progress…':'Run fictional discovery'}</button><button disabled={busy} onClick={()=>work(load)}>Refresh discovery</button></div>
  <p>This run evaluates every research mode for the selected horizon. Inputs are pinned historical fixtures, not current market data.</p>
  {error&&<p className="error" role="alert">{error}</p>}
  {run&&<p role="status">Execution: {label(run.status)} · {label(run.stage)}{run.error_code?' · '+label(run.error_code):''}</p>}
  {run?.status==='failed'&&<p className="notice">The latest scan failed. Any previous published batch below remains visible with its original timestamp.</p>}
  {data?.coverage&&<section className="panel" aria-label="Universe coverage"><h3>Universe coverage</h3><p>{data.coverage.screened} / {data.coverage.universe_total} fictional listings screened · {data.coverage.data_complete} with sufficient evidence · {data.coverage.research_complete} research complete · {data.coverage.research_failed} research unavailable</p><p>Batch: {label(data.status)} · Data through: {time(data.information_cutoff_at)}<br/>Published: {time(data.published_at)} · Next run: on request</p>{data.source_issues?.map(s=><p key={s}>{s}</p>)}</section>}
  {!data&&!error&&<p role="status">Loading discovery…</p>}
  {data&&!data.batch_id&&<p>No published batch yet. Run fictional discovery to ingest evidence and compare the three research modes.</p>}
  {data?.batch_id&&!data.recommendations.length&&<p>No qualifying picks in this published batch.</p>}
  {!!data?.recommendations.length&&<div className="table-wrap"><table><caption>Published {horizons.find(h=>h[0]===horizon)?.[1]} recommendations</caption><thead><tr><th>Company</th><th>Decision</th><th>Evidence</th><th>Paper admission</th><th>Details</th></tr></thead><tbody>{data.recommendations.map(r=><tr key={r.recommendation_id}><td>{r.instrument.symbol}</td><td><span className={'decision decision-'+r.action.toLowerCase()}>{label(r.action)}</span></td><td>{r.evidence_quality.missing_required.length?'Required evidence missing':r.research_status==='not_requested'?'Technical only':label(r.research_status)}</td><td>Blocked · no quantity</td><td><button disabled={busy} onClick={()=>work(()=>inspect(r))} aria-label={'Inspect '+r.instrument.symbol}>Inspect</button></td></tr>)}</tbody></table></div>}
  {data?.next_cursor&&<button disabled={busy} onClick={()=>work(async()=>{const p=await api(`/discovery?horizon=${horizon}&cohort=${cohort}&batch_id=${data.batch_id}&cursor=${encodeURIComponent(data.next_cursor!)}`);setData({...p,recommendations:[...data.recommendations,...p.recommendations]})})}>Load more</button>}
  {detail&&<section className="panel" aria-label="Discovery recommendation details"><h3>{detail.recommendation.instrument.symbol} · {label(detail.recommendation.action)}</h3><span className="badge">MOCK / SHADOW / NON-ACTIONABLE</span><p>{label(detail.recommendation.rationale.summary)}</p><dl className="record-meta"><dt>Recommendation ID</dt><dd>{detail.recommendation.recommendation_id}</dd><dt>Horizon</dt><dd>{detail.recommendation.horizon.duration} {label(detail.recommendation.horizon.units)} · Ends {time(detail.recommendation.horizon.holding_end_at)}</dd><dt>Entry expiry</dt><dd>{time(detail.recommendation.horizon.entry_expires_at)}</dd><dt>Next review</dt><dd>{time(detail.recommendation.horizon.next_review_at)}</dd></dl>
   <h4>Deterministic risk assessment</h4><p>Instrument: {label(detail.recommendation.risk_context.eligibility)} · Paper admission: {detail.recommendation.paper_admission.status}</p><p>{detail.recommendation.paper_admission.reason}</p><ul>{detail.recommendation.risk_context.binding_constraints.map(s=><li key={s}>{label(s)}</li>)}</ul>
   {detail.recommendation.execution&&<p>Conditional entry ₹{detail.recommendation.execution.entry_price} · Stop ₹{detail.recommendation.execution.stop_price}{detail.recommendation.execution.target_price?' · Trade target ₹'+detail.recommendation.execution.target_price:''}. No purchasable quantity.</p>}
   {detail.recommendation.valuation&&<p>Valuation scenario: ₹{detail.recommendation.valuation.low}–₹{detail.recommendation.valuation.high}. This is not a trading target.</p>}
   <h4>Quantitative signals</h4><dl className="signal-grid">{Object.entries(detail.quantitative.metrics).map(([k,v])=><div key={k}><dt>{label(k)}</dt><dd>{number(v)}</dd></div>)}</dl>
   <h4>AI research summary</h4>{detail.research?.assessment?.claims.map((c,i)=><p key={i}>{c.text}</p>)}{!detail.research?.assessment&&<p>{cohort==='quant'?'Quantitative only: no AI research requested.':'Research unavailable; no fallback to a successful AI label.'}</p>}
   <h4>Missing, conflicting evidence and uncertainty</h4><ul>{[...detail.recommendation.evidence_quality.missing_required,...detail.recommendation.evidence_quality.contradiction_ids.map(id=>'Conflicting evidence: '+id),...detail.recommendation.evidence_quality.uncertainty].map(s=><li key={s}>{label(s)}</li>)}</ul>
   <h4>Research mode comparison</h4><table><thead><tr><th>Mode</th><th>Decision</th><th>Research</th></tr></thead><tbody>{comparisons.map(r=><tr key={r.recommendation_id}><td>{modes.find(m=>m[0]===r.cohort.arm)?.[1]}</td><td>{label(r.action)}</td><td>{label(r.research_status)}</td></tr>)}</tbody></table><p>Same company, horizon and cutoff. AI cannot override quantitative or risk gates.</p>
   <h4>Citations and sources</h4>{!detail.citations.length&&<p>Quantitative inputs are preserved in the frozen provenance. Choose a researched mode to inspect document citations.</p>}{detail.citations.map((c,i)=><div key={c.evidence_id+'-'+i} className="citation"><p>{c.attribution} · {c.locator}</p><p>Source: {c.source_url}</p><blockquote>{c.excerpt??'Structured fact; see source record'}</blockquote><button disabled={busy} onClick={()=>work(async()=>setSource(await api('/evidence/'+encodeURIComponent(c.revision_id)+'?recommendation_id='+detail.recommendation.recommendation_id)))}>Inspect source {i+1}</button></div>)}
   {source&&<section aria-label="Source inspection"><h4>{source.document.title}</h4><p>{source.document.attribution}</p>{source.chunks.map((c,i)=><p key={i}>{c.text}</p>)}</section>}
   <details><summary>Conditions and immutable provenance</summary>{detail.recommendation.conditions.entry.map((c,i)=><p key={'entry'+i}>Entry: {c.explanation}</p>)}{detail.recommendation.conditions.invalidation.map((c,i)=><p key={'exit'+i}>Invalidation: {c.explanation}</p>)}<p>Published status: {detail.publication_status}</p><pre>{JSON.stringify({versions:detail.recommendation.versions,permissions:detail.permissions},null,2)}</pre></details>
  </section>}
 </section>
}
