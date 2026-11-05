import {useEffect,useState} from 'react'

type Research={status:string;analyzed_at?:string;listing_id?:string;identity_status?:string;company_name?:string;reasons?:string[];research_priority?:string;qualification_limitations?:string[];market_data?:{bars:number;latest_session:string;warmup_complete:boolean;freshness:{status:string}};technical?:{metrics:Record<string,string|null>}}
type Candidate={watchlist_key:string;source_label?:string;candidate_id:string;symbol:string;session_date:string;scanner:{scan_name:string;version:string};source_url:string;match_status:string;completeness:string;timestamp_basis:string;mode:string;research_status:string;error_code?:string;research:Research|null}
type Page={inbox?:Record<string,number>;failed_events?:{event_id:string;error_code:string}[];rows:Candidate[];total:number;session_date:string|null;delivery_status:string}

export function Candidates({onSelect,onUnauthorized,onSaved}:{onSelect:(id:string)=>void;onUnauthorized:()=>void;onSaved:()=>void}){
 const [data,setData]=useState<Page|null>(null),[error,setError]=useState(''),[session,setSession]=useState(''),[offset,setOffset]=useState(0),[entries,setEntries]=useState<Record<string,unknown>>({}),[message,setMessage]=useState(''),[version,setVersion]=useState(0)
 async function request(url:string,init?:RequestInit){const r=await fetch('/v1/real-research/'+url,init);if(r.status===401)onUnauthorized();if(!r.ok)throw Error('Candidates request failed: '+r.status);return r.json()}
 useEffect(()=>{let active=true
  async function refresh(){try{const [d,w]=await Promise.all([request('candidates?limit=100&offset='+offset+(session?'&session='+session:'')),request('watchlist')]);if(active){setData(d);setEntries(w.entries);setError('')}}catch(e){if(active){setData(null);setError(String(e))}}}
  setData(null);refresh();const timer=setInterval(refresh,15000)
  return()=>{active=false;clearInterval(timer)}
 },[session,offset,version])
 async function save(id:string){try{const w=await request('watchlist/'+encodeURIComponent(id),{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:'Researching',note:'',review_date:null})});setEntries(w.entries);setMessage('Candidate saved to watchlist');onSaved()}catch(e){setError(String(e))}}
 async function retry(id:string){try{await request('candidates/'+id+'/retry',{method:'POST'});setVersion(v=>v+1);setMessage('Stored research queued. Live acquisition remains disabled.')}catch(e){setError(String(e))}}
 return <section aria-label="Scanner candidates">
  <h3>Candidates</h3><p>Chartink discovers matches. Stock Discovery independently researches permitted stored evidence. Partial alerts do not describe the complete scanner universe; no delivery is not a zero-candidate day.</p>
  <label>Candidate session <input type="date" value={session} onChange={e=>{setSession(e.target.value);setOffset(0)}}/></label> <button onClick={()=>{setSession('');setOffset(0);setVersion(v=>v+1)}}>Latest candidates</button>
  {error&&<p role="alert">{error}</p>}{message&&<p role="status">{message}</p>}
  {!data&&!error&&<p>Loading candidate inbox…</p>}
  {data&&<><p>Inbox: {data.inbox?.pending??0} pending · {data.inbox?.failed??0} failed</p>{data.failed_events?.map(e=><p key={e.event_id}>{e.error_code}<button onClick={()=>retry('events/'+e.event_id)}>Retry failed delivery</button></p>)}<p data-testid="candidate-summary">{data.total} candidates · {data.session_date??'No session'} · {data.delivery_status.replaceAll('_',' ')}</p>
   <p>Continuing means observed in the previous represented session. New observed means absent from those prior results; new-versus-snapshot requires a complete preceding snapshot; neither certifies uninterrupted trading-session coverage. Receipt-date session hints are unverified.</p>
   <div className="table-wrap"><table><thead><tr><th>Scanner / session</th><th>Candidate / identity</th><th>Match / completeness</th><th>Market data / research</th><th>Independent priority / limitations</th><th>Actions</th></tr></thead><tbody>{data.rows.map(c=>{const r=c.research;const key=r?.listing_id??c.watchlist_key;return <tr key={c.candidate_id}>
    <td><a href={c.source_url} target="_blank" rel="noreferrer">{c.scanner.scan_name}</a><br/>v{c.scanner.version} · {c.session_date}<br/>{c.mode==='synthetic_fixture'?'SYNTHETIC FIXTURE':c.mode==='csv_recovery'?'CSV RECOVERY · UNVERIFIED':'Provider alert'}</td>
    <td><strong>{c.symbol}</strong><br/>{c.source_label?c.source_label+' (Chartink label; identity independently checked)':r?.company_name??'Company name unavailable'}<br/>{r?.identity_status?.replaceAll('_',' ')??'Identity pending'}<br/>{r?.listing_id}</td>
    <td>{c.match_status.replaceAll('_',' ')}<br/>{c.completeness.replaceAll('_',' ')}<br/>{c.timestamp_basis.replaceAll('_',' ')}</td>
    <td>{c.research_status}<br/>Analysis at {r?.analyzed_at??'Pending'}<br/>{r?.market_data?`${r.market_data.bars} bars · ${r.market_data.latest_session??'No price session'} · ${r.market_data.freshness.status}`:'History unavailable or not checked'}<details><summary>Technical observations</summary>{Object.entries(r?.technical?.metrics??{}).map(([k,v])=><p key={k}>{k}: {v??'Unavailable'}</p>)}</details></td>
    <td>{r?.research_priority?.replaceAll('_',' ')??'Not rankable'}<details><summary>Evidence limitations</summary>{[...r?.reasons??[],...r?.qualification_limitations??[],c.error_code??''].filter(Boolean).map((s,i)=><p key={i}>{s.replaceAll('_',' ')}</p>)}<p>No approved live request budget. Historical point-in-time eligibility and trading qualification remain blocked.</p></details></td>
    <td>{r?.listing_id&&<button onClick={()=>onSelect(r.listing_id!)}>Open {c.symbol} research</button>}{entries[key]||entries[c.watchlist_key]?<p>Saved to watchlist</p>:<button onClick={()=>save(key)}>Save {c.symbol} to watchlist</button>}{c.research_status!=='pending'&&<button onClick={()=>retry(c.candidate_id)}>Retry stored research</button>}</td>
   </tr>})}</tbody></table></div>
   <button disabled={offset===0} onClick={()=>setOffset(Math.max(0,offset-100))}>Previous candidates</button><button disabled={offset+100>=data.total} onClick={()=>setOffset(offset+100)}>More candidates</button>
  </>}
 </section>
}
