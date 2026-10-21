import { RealCompany } from './RealCompany'
import { useEffect, useState } from 'react'

type Status = {status:string;providers:{id:string;adapter:string;coverage:string;blockers:string[]}[];blockers:string[];limitations:string[];models:{note:string};scheduler:{prices:string};forward_paper:{reason:string}}
const horizons=[['swing','Swing · 2–10 trading days'],['short_term','Short-term · 1–3 months'],['long_term','Long-term · 1–5 years']]
export function RealResearch({onUnauthorized}:{onUnauthorized:()=>void}) {
 const [data,setData]=useState<Status|null>(null),[error,setError]=useState(''),[horizon,setHorizon]=useState('swing')
 useEffect(()=>{let active=true
  fetch('/v1/real-research/status').then(async response=>{if(response.status===401)onUnauthorized();if(!response.ok)throw new Error('Real research status is unavailable.');return response.json()}).then(result=>{if(active)setData(result)}).catch(e=>{if(active)setError(e.message)})
  return()=>{active=false}
 },[])
 return <section className="discovery" aria-label="Real research">
  <div className="discovery-heading"><div><p className="eyebrow">REAL RESEARCH</p><h2>Indian market research</h2><p>Actual-company research requires connected, permitted sources and verified evidence.</p></div><span className="badge">BLOCKED · NON-ACTIONABLE</span></div>
  <div role="tablist" aria-label="Real investment horizon" className="horizon-tabs">{horizons.map(([id,name])=><button key={id} role="tab" aria-selected={horizon===id} onClick={()=>setHorizon(id)}>{name}</button>)}</div>
  <RealCompany horizon={horizon} onUnauthorized={onUnauthorized}/>
  {error&&<p role="alert" className="error">{error}</p>}
  {!data&&!error&&<p role="status">Checking real research availability…</p>}
  {data&&<>
   <section className="panel" aria-label="Real research blockers"><h3>Qualification and publication gates</h3><ul>{data.blockers.map(s=><li key={s}>{s}</li>)}</ul><p>Only permitted records appear above. Unavailable inputs cannot produce entry conditions, targets or performance results.</p></section>
   <section className="panel"><h3>Source coverage</h3><table><thead><tr><th>Source</th><th>Coverage</th><th>Status</th></tr></thead><tbody>{data.providers.map(p=><tr key={p.id}><td>{p.id}</td><td>{p.coverage}</td><td>{p.adapter.replaceAll('_',' ')}<ul>{p.blockers.map(b=><li key={b}>{b.replaceAll('_',' ')}</li>)}</ul></td></tr>)}</tbody></table></section>
   <section className="panel"><h3>Local AI and automatic operation</h3><p>{data.models.note}</p><p>{data.scheduler.prices}. Automatic research, events and outcomes remain blocked.</p><h3>Forward paper</h3><p>{data.forward_paper.reason}</p></section>
   <ul>{data.limitations.map(s=><li key={s}>{s}</li>)}</ul>
  </>}
 </section>
}
