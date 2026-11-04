import {useEffect,useState} from 'react'
type Observation={code:string;text:string}
type Report={version:string;state:string;evaluated_at:string;research_only:boolean;changes_since_scheduled_run:string;
 market:{chart_points:number;freshness:{latest_available_price_session:string|null;latest_verified_closed_session:string|null;status:string};coverage:{missing_sessions:string[]};limitations:string[]};
 technical:{interpretation:{bullish:Observation[];bearish:Observation[];neutral:Observation[]}};
 fundamentals:{status:string;facts:{fact_id:string;metric:string;value:string|null;unit:string;period_end_at:string;age_days:number;source_locator:string|null;source_url?:string|null}[];conflict_validation:string;missing:string[];conflicts:unknown[];limitations:string[]};
 news?:{status:string;reason:string;coverage:string};
 ai:{status:string;reason:string;new_model_calls:number;research:null|{findings:{text:string;citations:{source_url:string;locator:string}[]}[]}};
 conclusion:{summary:string;uncertainties:string[];missing_qualification:string[]};hypothetical_levels:{status:string;reason:string};
 automation:{automation:string;latest_successful_analysis_at:string|null;latest_run:null|{status:string;error:string|null;at:string;catch_up:boolean}};
 acquisition:{status:string;reason:string;last_attempt_at:string|null}}
export function DailyInsight({listing,onUnauthorized,onRefresh}:{listing:string;onUnauthorized:()=>void;onRefresh:()=>void}){
 const [data,setData]=useState<Report|null>(null),[error,setError]=useState('')
 useEffect(()=>{setData(null);setError('');const c=new AbortController()
 fetch('/v1/real-research/companies/'+encodeURIComponent(listing)+'/insight',{signal:c.signal}).then(async r=>{
  if(r.status===401)onUnauthorized()
  if(!r.ok)throw Error(r.status===403?'Denied: current source permissions do not allow this report.':'Analysis unavailable: verified inputs could not be read.')
  const d=await r.json();if(d.version!=='infy-daily-insight-1')throw Error('Analysis unavailable: unsupported report.')
  if(!c.signal.aborted)setData(d)
 }).catch(e=>{if(e.name!=='AbortError')setError(e.message)})
 return()=>c.abort()},[listing])
 return <section className="panel" aria-label="Daily INFY insight"><h3>Daily INFY research · non-actionable</h3>
 <button onClick={()=>{setData(null);onRefresh()}}>Review latest stored evidence</button>
 {error&&<p role="alert">{error}</p>}
 {!data&&!error&&<p>Reading permitted stored evidence…</p>}
 {data&&<><p data-testid="insight-state">{data.state.replaceAll('_',' ')} · evaluated {data.evaluated_at}</p>
 <p>{data.market.chart_points} qualified descriptive bars. Prices through {data.market.freshness.latest_available_price_session??'unavailable'}; latest verified closed stored session {data.market.freshness.latest_verified_closed_session??'unavailable'}. {data.market.freshness.status.replaceAll('_',' ')}.</p>
 <p>Missing sessions: {data.market.coverage.missing_sessions.join(', ')||'None in stored calendar window'}. Calendar completeness is not attested.</p>
 <h4>Technical interpretation</h4>{(['bullish','bearish','neutral'] as const).map(group=><div key={group}><strong>{group==='neutral'?'Context and conditions':group+' observations'}</strong><ul>{data.technical.interpretation[group].map(o=><li key={o.code}>{o.text}</li>)}</ul></div>)}
 <h4>Fundamental evidence</h4><p>{data.fundamentals.status.replaceAll('_',' ')}. Conflict validation: {data.fundamentals.conflict_validation.replaceAll('_',' ')}; {data.fundamentals.conflicts.length} verified conflict entries available. {data.fundamentals.limitations.join(' ')}</p>
 <details><summary>Reported metrics and periods ({data.fundamentals.facts.length})</summary><ul>{data.fundamentals.facts.map(f=><li key={f.fact_id}>{f.metric}: {f.value??'Unavailable'} {f.unit}; period ended {f.period_end_at}; {f.age_days} days since period end. Source: {f.source_url?<a href={f.source_url} target="_blank" rel="noreferrer">{f.source_locator??'Reported source'}</a>:f.source_locator??'Unavailable'}</li>)}</ul></details>
 <h4>News and events</h4><p>{data.news?.status??'UNAVAILABLE'} · {(data.news?.reason??'permitted_complete_news_event_coverage_missing').replaceAll('_',' ')}. Missing news is not evidence of no adverse events.</p>
 <h4>AI research</h4><p data-testid="insight-ai">{data.ai.status} · {data.ai.reason.replaceAll('_',' ')}. New model calls: {data.ai.new_model_calls}.</p>
 <ul>{data.ai.research?.findings.map((f,i)=><li key={i}>{f.text} {f.citations.map((c,j)=><a key={j} href={c.source_url} target="_blank" rel="noreferrer">{c.locator} </a>)}</li>)}</ul>
 <h4>Research conclusion</h4><p>{data.conclusion.summary}</p><p>Hypothetical entry, stop and target: {data.hypothetical_levels.status} — {data.hypothetical_levels.reason.replaceAll('_',' ')}.</p>
 <ul>{data.conclusion.uncertainties.map(s=><li key={s}>{s.replaceAll('_',' ')}</li>)}</ul>
 <details><summary>Missing qualification requirements</summary><ul>{data.conclusion.missing_qualification.map(s=><li key={s}>{s.replaceAll('_',' ')}</li>)}</ul></details>
 <h4>Daily operation</h4><p>Automation: {data.automation.automation.replaceAll('_',' ')}. Latest successful scheduled analysis: {data.automation.latest_successful_analysis_at??'No successful scheduled run recorded'}.</p>
 <p>Last run: {data.automation.latest_run?`${data.automation.latest_run.status} at ${data.automation.latest_run.at}; ${data.automation.latest_run.error??'no recorded error'}; catch-up ${data.automation.latest_run.catch_up}`:'None recorded'}.</p>
 <p>Acquisition: {data.acquisition.status}; last attempt: {data.acquisition.last_attempt_at??'None in this stored-evidence pipeline'}. {data.acquisition.reason.replaceAll('_',' ')}.</p>
 <p>Since previous scheduled analysis: {data.changes_since_scheduled_run.replaceAll('_',' ')}.</p>
 <p>No BUY/SELL signal, trading, paper admission or validated historical performance. Descriptive observations do not predict returns.</p></>}
 </section>
}
