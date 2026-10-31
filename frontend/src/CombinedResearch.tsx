import {useRef,useState,useEffect} from 'react'
type Citation={evidence_id:string;revision_id:string;source_url:string;locator:string}
type Finding={text:string;citations:Citation[]}
type Trend=Finding&{candidate_id:string;metric:string;value:string;unit:string;formula:string|null}
export type CombinedReport={report_id:string;mode:string;status:string;analysis_cutoff_at:string;conclusion:string;gaps:string[];acceptance_gates:Record<string,string>;technical:{condition:string;indicators:Record<string,string|null>;reasons:string[]};financial:null|{run_id:string;cutoff_at:string;model:{id:string;version:string;content_hash:string}|null;prompt_hash:string;validator_version:string;trends:Trend[];findings:Finding[];interpretations:Finding[];source_excerpts:Finding[];uncertainties:string[];conflicts:string[][];pending_interpretation_count:number;excerpt_warning:string};replay:{status:string;future_outcomes:string;limitation:string}}
function Citations({items}:{items:Citation[]}){return <ul>{items.map((c,i)=><li key={i}><a href={c.source_url} target="_blank" rel="noreferrer">{c.locator}</a> · Revision {c.revision_id}</li>)}</ul>}
export function CombinedSummary({report}:{report:CombinedReport}){
 const f=report.financial
 return <section aria-label="Combined research result"><h4>Technical + financial research</h4>
 <p><strong>INSUFFICIENT EVIDENCE · Research only</strong></p><p>{report.conclusion}</p>
 <p>As-of {report.analysis_cutoff_at} · {report.mode==='synthetic_replay'?'Synthetic frozen replay; fictional market data':'Stored observed evidence; real qualification remains blocked'}.</p>
 <h4>Technical conditions</h4><p>{report.technical.condition.replaceAll('_',' ')}</p>
 <ul>{report.technical.reasons.map((r,i)=><li key={i}>{r.replaceAll('_',' ')}</li>)}</ul>
 <dl>{Object.entries(report.technical.indicators).map(([k,v])=><div key={k}><dt>{k}</dt><dd>{v??'Unavailable'}</dd></div>)}</dl>
 <h4>Financial trends and earnings changes</h4>
 {f?<><p>Stored research cutoff {f.cutoff_at}. Model {f.model?.id??'Unspecified'} · {f.model?.version??''}. No new inference is requested by this view.</p>
 <p>These comparisons are deterministic calculations; they are not model accuracy measurements.</p>
 {f.trends.map(t=><article key={t.candidate_id}><p>{t.text}</p><details><summary>Calculation and citations</summary><p>{t.formula} · exact {t.value} {t.unit}</p><Citations items={t.citations}/></details></article>)}
 <h4>Supported model-selected findings</h4>{[...f.findings,...f.interpretations].map((x,i)=><article key={i}><p>{x.text}</p><Citations items={x.citations}/></article>)}
 {!f.findings.length&&!f.interpretations.length&&<p>No supported model finding in this report.</p>}
 <h4>Company statements and announcements</h4><p>{f.excerpt_warning}</p>{f.source_excerpts.map((x,i)=><article key={i}><blockquote>{x.text}</blockquote><Citations items={x.citations}/></article>)}
 {!f.source_excerpts.length&&<p>No validated source excerpt; announcement coverage is unknown.</p>}
 <h4>Financial risks and unresolved evidence</h4><ul>{f.uncertainties.map((s,i)=><li key={i}>{s}</li>)}</ul>
 <p>{f.conflicts.length} conflicting evidence group(s); {f.pending_interpretation_count} unaccepted interpretation(s). Missing coverage never means no risk.</p>
 <details><summary>Research provenance</summary><p>Run {f.run_id} · Prompt {f.prompt_hash} · Verifier {f.validator_version} · Model digest {f.model?.content_hash??'Unavailable'}</p></details>
 </>:<p>No eligible verified financial research. Missing evidence is not filled with a model guess or a synthetic report.</p>}
 <h4>Acceptance gates and source gaps</h4><ul>{report.gaps.map(g=><li key={g}>{g.replaceAll('_',' ')}</li>)}</ul>
 <p>Publication, paper admission and trading remain blocked. No entry, stop, target or quantity is issued by this combined view.</p>
 <h4>Historical evaluation</h4><p>{report.replay.status.replaceAll('_',' ')} · {report.replay.future_outcomes.replaceAll('_',' ')}.</p><p>{report.replay.limitation}</p>
 <details><summary>Deterministic report identity</summary>{report.report_id}</details></section>
}
export function CombinedResearch({listing,onUnauthorized}:{listing:string;onUnauthorized:()=>void}){
 const [cutoff,setCutoff]=useState(''),[report,setReport]=useState<CombinedReport|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false)
 const active=useRef<AbortController|null>(null)
 const clear=()=>{active.current?.abort();active.current=null;setReport(null);setError('');setBusy(false)}
 useEffect(()=>()=>{active.current?.abort()},[])
 async function load(){clear();const c=new AbortController();active.current=c;setBusy(true)
  try{const q=new URLSearchParams({analysis:'combined'});if(cutoff)q.set('cutoff_at',cutoff)
   const r=await fetch('/v1/real-research/companies/'+encodeURIComponent(listing)+'?'+q,{signal:c.signal,cache:'no-store'})
   if(r.status===401)onUnauthorized()
   if(!r.ok)throw Error(r.status===403?'Source permission denied.':r.status===422?'Use a valid UTC cutoff.':'Combined research is unavailable.')
   const value=await r.json();if(!c.signal.aborted)setReport(value)
  }catch(e){if(!c.signal.aborted)setError(e instanceof Error?e.message:'Combined research is unavailable.')}
  finally{if(!c.signal.aborted)setBusy(false)}
 }
 return <section aria-label="Combined company research"><h3>Combined research preview</h3><p>Compare existing technical evidence with cited financial research. No new model calls or actionable recommendation.</p>
 <label>Combined cutoff (UTC, optional)<input value={cutoff} onChange={e=>{clear();setCutoff(e.target.value)}} placeholder="2026-10-31T10:00:00Z"/></label>
 <button disabled={busy} onClick={load}>{busy?'Loading stored evidence…':'Compare stored research'}</button>
 {error&&<p role="alert">{error}</p>}{report&&<CombinedSummary report={report}/>}</section>
}
