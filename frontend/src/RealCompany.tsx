import {useEffect,useState} from 'react'
import {Chart} from './PriceChart'
type Citation={source_url:string;locator:string;attribution:string}
type Company={symbol:string;isin:string;cutoff_at:string;price_series:{time:string;open:string;high:string;low:string;close:string;volume:number}[];financial_facts:{fact_id:string;metric:string;value:string|null;unit:string;period_end_at:string;scope:string;source_locator:string|null}[];documents:{title:string;revision:{data:{url:string};published_at:string}}[];events:{claim_id:string;statement:string;status:string}[];quantitative:Record<string,{action:string;reasons:string[];metrics:Record<string,string|null>}>;analysis_history:{run_id:string;cutoff_at:string;horizon:string;result:{status:string;assessment?:{action:string;claims:{text:string;citations:Citation[]}[];missing:string[]}};citations:Citation[]}[];limitations:string[]}
export function RealCompany({horizon,onUnauthorized}:{horizon:string;onUnauthorized:()=>void}){
 const [list,setList]=useState<string[]>([]),[listing,setListing]=useState(''),[data,setData]=useState<Company|null>(null),[error,setError]=useState(''),[version,setVersion]=useState(0)
 useEffect(()=>{const c=new AbortController();fetch('/v1/real-research/companies',{signal:c.signal}).then(async r=>{if(r.status===401)onUnauthorized();if(r.status===503)return {listing_ids:[]};if(!r.ok)throw Error('Company configuration is unavailable');return r.json()}).then(d=>{setList(d.listing_ids);setListing(d.listing_ids[0]??'')}).catch(e=>{if(e.name!=='AbortError')setError('Company configuration is unavailable')});return()=>c.abort()},[])
 useEffect(()=>{setData(null);setError('');if(!listing)return;const c=new AbortController();fetch('/v1/real-research/companies/'+encodeURIComponent(listing),{signal:c.signal}).then(async r=>{if(r.status===401)onUnauthorized();if(!r.ok)throw Error(r.status===403?'Source permission denied':'Real company inputs are unavailable');return r.json()}).then(d=>{if(!c.signal.aborted)setData(d)}).catch(e=>{if(e.name!=='AbortError')setError(e.message)});return()=>c.abort()},[listing,version])
 if(!list.length&&!error)return null
 const quant=data?.quantitative[horizon]
 return <section className="panel" aria-label="Observed company research"><h3>Observed company evidence</h3>
 <label>Company <select value={listing} onChange={e=>setListing(e.target.value)}>{list.map(s=><option key={s}>{s}</option>)}</select></label>
 <button onClick={()=>{setData(null);setVersion(version+1)}}>Refresh real evidence</button>
 {error&&<p role="alert">{error}</p>}
 {data&&<><h3>{data.symbol} · {data.isin}</h3><p>Inputs known at {data.cutoff_at}. Experimental analysis · no published prediction.</p>
 {data.price_series.length?<Chart real bars={data.price_series.map(b=>({time:b.time,open:Number(b.open),high:Number(b.high),low:Number(b.low),close:Number(b.close)}))}/>:<p>Permitted price history is unavailable.</p>}
 <h4>Financial facts</h4>{data.financial_facts.length?<table><thead><tr><th>Metric</th><th>Value / unit</th><th>Period / scope</th><th>Source location</th></tr></thead><tbody>{data.financial_facts.map(f=><tr key={f.fact_id}><td>{f.metric.replaceAll('_',' ')}</td><td>{f.value??'Not reported'} {f.unit}</td><td>{f.period_end_at.slice(0,10)} · {f.scope}</td><td>{f.source_locator??'Derived calculation'}</td></tr>)}</tbody></table>:<p>No financial facts ingested.</p>}
 <h4>Source documents</h4><ul>{data.documents.map(d=><li key={d.revision.data.url}><a href={d.revision.data.url} target="_blank" rel="noreferrer">{d.title}</a> · Published {d.revision.published_at}</li>)}</ul>
 <h4>Events</h4>{data.events.length?<ul>{data.events.map(e=><li key={e.claim_id}>{e.statement} · {e.status}</li>)}</ul>:<p>No ingested event coverage.</p>}
 <h4>Quantitative assessment</h4><p>{quant?.action.replaceAll('_',' ')}</p><ul>{quant?.reasons.map(r=><li key={r}>{r.replaceAll('_',' ')}</li>)}</ul><dl>{Object.entries(quant?.metrics??{}).map(([k,v])=><div key={k}><dt>{k}</dt><dd>{v??'Unavailable'}</dd></div>)}</dl>
 <h4>Local research history</h4>{data.analysis_history.filter(r=>r.horizon===horizon).map(r=><article key={r.run_id}><p>{r.cutoff_at} · {r.result.status}</p>{r.result.assessment?.claims.map((c,i)=><p key={i}>{c.text} {c.citations.map((s,j)=><a key={j} href={s.source_url} target="_blank" rel="noreferrer">[{s.locator}] </a>)}</p>)}<ul>{r.result.assessment?.missing.map(m=><li key={m}>{m}</li>)}</ul></article>)}
 <ul>{data.limitations.map(l=><li key={l}>{l}</li>)}</ul></>}
 </section>
}
