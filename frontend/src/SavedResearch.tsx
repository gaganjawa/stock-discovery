import {useEffect,useRef,useState} from 'react'
import type {Analysis,Info} from './App'
type Run={recommendation_id:string;availability:string;instrument_id?:string;cutoff_at?:string;generated_at?:string;dataset_version?:string;cohort?:string;action?:string;outcome_recorded?:boolean}
type History={runs:Run[];next_cursor:string|null;evaluation:{status:string;paired_sample_size:number;reason:string;scope:string;counts:Record<string,number>;limitation:string}}
export function SavedResearch({datasets,initialDataset,onOpen,onClear,onUnauthorized}:{datasets:string[];initialDataset:string;onOpen:(a:Analysis,i:Info)=>void;onClear:()=>void;onUnauthorized:()=>void}){
 const [dataset,setDataset]=useState(initialDataset),[instrument,setInstrument]=useState(''),[cursor,setCursor]=useState(''),[version,setVersion]=useState(0)
 const [history,setHistory]=useState<History|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[notice,setNotice]=useState('')
 const active=useRef<AbortController|null>(null)
 async function get(path:string,c:AbortController){const r=await fetch('/api/v1'+path,{signal:c.signal,cache:'no-store'});if(r.status===401)onUnauthorized();if(!r.ok)throw Error(r.status===403?'Saved evidence is restricted.':'Saved research is unavailable.');return r.json()}
 useEffect(()=>{active.current?.abort();const c=new AbortController();active.current=c;setHistory(null);setError('');setBusy(true)
  const query=new URLSearchParams({limit:'20'});if(dataset)query.set('dataset_version',dataset);if(instrument)query.set('instrument_id',instrument);if(cursor)query.set('before',cursor)
  get('/analysis?'+query,c).then(value=>{if(!c.signal.aborted)setHistory(value)}).catch(e=>{if(!c.signal.aborted)setError(e.message)}).finally(()=>{if(!c.signal.aborted)setBusy(false)})
  return()=>c.abort()
 },[dataset,instrument,cursor,version])
 async function open(id:string){active.current?.abort();const c=new AbortController();active.current=c;onClear();setError('');setBusy(true)
  try{const a=await get('/analysis/'+encodeURIComponent(id),c);const i=await get('/datasets/'+encodeURIComponent(a.recommendation.versions.dataset),c);if(!c.signal.aborted)onOpen(a,i)}
  catch(e){if(!c.signal.aborted)setError(e instanceof Error?e.message:'Saved research is unavailable.')}
  finally{if(!c.signal.aborted)setBusy(false)}
 }
 async function batch(){active.current?.abort();const c=new AbortController();active.current=c;setBusy(true);setError('');setNotice('')
  try{const info:Info=await get('/datasets/'+encodeURIComponent(dataset),c);const dates=[39,59,79].map(n=>info.dates[n]).filter(Boolean)
   if(dates.length!==3)throw Error('This dataset lacks the three demonstration dates.')
   const r=await fetch('/api/v1/experiments',{method:'POST',headers:{'Content-Type':'application/json'},signal:c.signal,body:JSON.stringify({dataset_version:dataset,dates,include_financial:true})})
   if(r.status===401)onUnauthorized();if(!r.ok)throw Error('Historical batch could not be queued.')
   const queued=await r.json();if(!c.signal.aborted)setNotice(`${queued.job_ids.length} fictional replay jobs queued. Refresh saved research after completion; failed jobs remain visible on Dashboard.`)
  }catch(e){if(!c.signal.aborted)setError(e instanceof Error?e.message:'Historical batch is unavailable.')}
  finally{if(!c.signal.aborted)setBusy(false)}
 }
 useEffect(()=>()=>{active.current?.abort()},[])
 return <section className="panel demo" aria-label="Saved historical research"><h2>Saved historical research</h2><p>Reopen immutable decisions across dates and instruments. Future prices stay hidden until you choose Reveal.</p>
 <div className="controls"><label>Saved dataset<select value={dataset} onChange={e=>{setDataset(e.target.value);setCursor('');onClear()}}><option value="">All datasets</option>{datasets.map(d=><option key={d} value={d}>{d.slice(0,16)}…</option>)}</select></label>
 <label>Saved instrument<input value={instrument} placeholder="All instruments" onChange={e=>{setInstrument(e.target.value);setCursor('');onClear()}}/></label>
 <button disabled={busy} onClick={()=>setVersion(v=>v+1)}>Refresh saved research</button><button disabled={busy||!dataset} onClick={batch}>Evaluate fictional evidence batch</button></div>
 {notice&&<p role="status">{notice}</p>}{error&&<p role="alert">{error}</p>}
 {history&&<><p>AI-versus-technical evaluation: {history.evaluation.status} · eligible paired samples {history.evaluation.paired_sample_size}.</p><p>{history.evaluation.reason.replaceAll('_',' ')}. {history.evaluation.limitation}</p><p>Counts on this page: {Object.entries(history.evaluation.counts).map(([k,v])=>k.replaceAll('_',' ')+': '+v).join(' · ')}.</p>
 {!history.runs.length?<p>No saved research matches these filters.</p>:<div className="table-wrap"><table><thead><tr><th>Instrument / cutoff</th><th>Evidence</th><th>Decision</th><th>Outcome history</th><th>Open</th></tr></thead><tbody>{history.runs.map(r=><tr key={r.recommendation_id} data-run-id={r.recommendation_id}>{r.availability==='available'?<><td>{r.instrument_id}<br/>{r.cutoff_at}</td><td>{r.cohort?.replaceAll('_',' ')} · synthetic</td><td>{r.action?.replaceAll('_',' ')}</td><td>{r.outcome_recorded?'Recorded; hidden until Reveal':'Not evaluated'}</td><td><button disabled={busy} onClick={()=>open(r.recommendation_id)} aria-label={'Open saved '+r.instrument_id+' '+r.cutoff_at+' '+r.cohort}>Open frozen research</button></td></>:<td colSpan={5}>Evidence restricted or unavailable. Source content withheld.</td>}</tr>)}</tbody></table></div>}
 <button disabled={busy||!cursor} onClick={()=>setCursor('')}>Newest research</button> <button disabled={busy||!history.next_cursor} onClick={()=>setCursor(history.next_cursor??'')}>Older research</button>
 </>}
 </section>
}
