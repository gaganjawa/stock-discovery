import { useEffect, useState } from 'react'

type Refresh={current:boolean;latest_session:string|null;latest_bar:string|null;missing_sessions:number}
type Row = {listing_id:string;symbol?:string;state:'available'|'unavailable'|'denied';reasons:string[];sessions?:number;last_session?:string|null;indicators?:string[];refresh?:Refresh}
// STK-079: plain-language reasons for the configured pilot; codes stay visible for support.
const REASONS:Record<string,string>={
 source_permission_denied:'No current permitted grant covers this read.',
 real_identity_missing_or_ambiguous:'No single verified company identity is stored.',
 adjusted_observations_unavailable:'Too few stored daily prices (30 needed).',
 session_coverage_unavailable:'Stored prices have gaps against the NSE calendar.',
 session_boundaries_unverified:'Candle open/close times do not match verified NSE sessions.',
 batch_identity_missing_or_ambiguous:'Prices come from several downloads; the multi-stream rule is not approved.',
 adjusted_stream_conflict:'Two downloads disagree on the same day; possible re-adjustment.',
 adjusted_stream_continuity_unverified:'Downloads do not overlap, so continuity cannot be proven.',
 batch_provenance_unverified:'Stored page hashes or provenance do not verify.',
 ambiguous_price_sources:'More than one price source claims the same day.',
}
export const explain=(code:string)=>REASONS[code]??code.replaceAll('_',' ')

const day=(t?:string|null)=>t?t.slice(0,10):'unknown'
// STK-079: one-glance daily note from stored observations; it never fetches or infers prices.
export function DailyNote({rows}:{rows:Row[]}) {
 const name=(r:Row)=>r.symbol??r.listing_id
 const latest=rows.map(r=>r.refresh?.latest_session).filter(Boolean).sort().pop()
 const current=rows.filter(r=>r.refresh?.current),blocked=rows.filter(r=>!r.refresh)
 const stale=rows.filter(r=>r.refresh&&!r.refresh.current)
 return <div className="daily-note" data-testid="daily-coverage-note">
  <p><strong>Daily note · latest verified session {day(latest)}</strong> · {current.length} of {rows.length} refreshed.</p>
  {stale.length>0&&<p data-testid="daily-note-stale">Behind: {stale.map(r=>`${name(r)} (last price ${day(r.refresh!.latest_bar)}${r.refresh!.missing_sessions?`, ${r.refresh!.missing_sessions} sessions missing`:''})`).join('; ')}.</p>}
  {blocked.length>0&&<p data-testid="daily-note-blocked">Not readable: {blocked.map(r=>`${name(r)} (${explain(r.reasons[0]??'inputs_unavailable')})`).join('; ')}</p>}
  {!stale.length&&!blocked.length&&<p>Nothing missing.</p>}
 </div>
}

export function PilotCoverage({onSelect,onUnauthorized}:{onSelect:(id:string)=>void;onUnauthorized:()=>void}) {
 const [rows,setRows]=useState<Row[]|null>(null),[error,setError]=useState('')
 useEffect(()=>{let active=true
  fetch('/v1/real-research/coverage').then(async r=>{if(r.status===401)onUnauthorized();if(!r.ok){const d=await r.json().catch(()=>({}));throw Error(typeof d.detail==='string'?d.detail:'Pilot coverage is unavailable.')}return r.json()})
   .then(d=>{if(active)setRows(d.rows)}).catch(e=>{if(active)setError(e.message)})
  return()=>{active=false}},[])
 if(error)return <p role="alert" className="error" data-testid="pilot-coverage-error">{error}</p>
 if(!rows)return <p role="status">Checking pilot coverage…</p>
 const ready=rows.filter(r=>r.state==='available').length
 return <section className="panel" aria-label="Pilot coverage" data-testid="pilot-coverage">
  <h3>Pilot coverage · {ready} of {rows.length} companies readable (descriptive only)</h3>
  <DailyNote rows={rows}/>
  <table><thead><tr><th>Company</th><th>State</th><th>Detail</th><th></th></tr></thead><tbody>{rows.map(r=><tr key={r.listing_id} data-testid={`pilot-row-${r.listing_id}`}>
   <td>{r.symbol??r.listing_id}</td><td>{r.state==='available'?'Chart and indicators':r.state==='denied'?'Permission denied':'Unavailable'}</td>
   <td>{r.state==='available'?`${r.sessions} sessions to ${r.last_session} · ${r.indicators?.join(', ')}`:<ul>{r.reasons.map(c=><li key={c} title={c}>{explain(c)}</li>)}</ul>}</td>
   <td><button onClick={()=>onSelect(r.listing_id)} data-testid={`pilot-open-${r.listing_id}`}>Open</button></td></tr>)}</tbody></table>
 </section>
}
