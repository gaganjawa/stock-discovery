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
 real_read_access_denied:'The saved grant does not allow this read (expired, revoked, retention or scope).',
 source_revoked:'The saved grant has been revoked.',
 ambiguous_source_grant:'More than one saved grant matches this source account.',
 listing_not_configured:'This company is not in the view configuration.',
 inputs_unavailable:'Stored inputs could not be read; check the API terminal for request_failed lines.',
}
export const explain=(code:string)=>REASONS[code]??code.replaceAll('_',' ')

const day=(t?:string|null)=>t?t.slice(0,10):'unknown'
// STK-079: one-glance daily note from stored observations; it never fetches or infers prices.
export function DailyNote({rows}:{rows:Row[]}) {
 const name=(r:Row)=>r.symbol??r.listing_id
 const latest=rows.map(r=>r.refresh?.latest_session).filter(Boolean).sort().pop()
 const current=rows.filter(r=>r.refresh?.current),blocked=rows.filter(r=>r.state!=='available')
 const stale=rows.filter(r=>r.refresh&&!r.refresh.current),ready=rows.length-blocked.length
 return <div className="daily-note" data-testid="daily-coverage-note">
  <p><strong>Daily note · latest verified session {day(latest)}</strong> · prices current for {current.length} of {rows.length} · charts readable for {ready} of {rows.length}.</p>
  {stale.length>0&&<p data-testid="daily-note-stale">Prices behind: {stale.map(r=>`${name(r)} (last price ${day(r.refresh!.latest_bar)}${r.refresh!.missing_sessions?`, ${r.refresh!.missing_sessions} sessions missing`:''})`).join('; ')}.</p>}
  {blocked.length>0&&<p data-testid="daily-note-blocked">Chart not readable: {blocked.map(r=>`${name(r)} (${explain(r.reasons[0]??'inputs_unavailable')})`).join('; ')}</p>}
  {!stale.length&&!blocked.length&&<p>Nothing missing.</p>}
 </div>
}

export function PilotCoverage({onSelect,onUnauthorized,onLabels}:{onSelect:(id:string)=>void;onUnauthorized:()=>void;onLabels?:(labels:Record<string,string>)=>void}) {
 const [rows,setRows]=useState<Row[]|null>(null),[error,setError]=useState('')
 useEffect(()=>{let active=true
  fetch('/v1/real-research/coverage').then(async r=>{if(r.status===401)onUnauthorized();if(!r.ok){const d=await r.json().catch(()=>({}));throw Error(typeof d.detail==='string'?d.detail:'Pilot coverage is unavailable.')}return r.json()})
   .then(d=>{if(active){setRows(d.rows);onLabels?.(Object.fromEntries(d.rows.filter((r:Row)=>r.symbol).map((r:Row)=>[r.listing_id,r.symbol!])))}}).catch(e=>{if(active)setError(e.message)})
  return()=>{active=false}},[])
 if(error)return <p role="alert" className="error" data-testid="pilot-coverage-error">{error}</p>
 if(!rows)return <p role="status">Checking pilot coverage…</p>
 const ready=rows.filter(r=>r.state==='available').length
 return <section className="panel" aria-label="Pilot coverage" data-testid="pilot-coverage">
  <h3>Pilot coverage · {ready} of {rows.length} companies readable (descriptive only)</h3>
  <DailyNote rows={rows}/>
  <div className="table-wrap"><table><thead><tr><th>Company</th><th>State</th><th>Detail</th><th></th></tr></thead><tbody>{rows.map(r=><tr key={r.listing_id} data-testid={`pilot-row-${r.listing_id}`}>
   <td>{r.symbol??r.listing_id}</td><td>{r.state==='available'?'Chart and indicators':r.state==='denied'?'Permission denied':'Unavailable'}</td>
   <td>{r.state==='available'?`${r.sessions} sessions to ${r.last_session} · ${r.indicators?.join(', ')}`:<ul>{r.reasons.map(c=><li key={c} title={c}>{explain(c)}</li>)}</ul>}</td>
   <td><button onClick={()=>onSelect(r.listing_id)} data-testid={`pilot-open-${r.listing_id}`}>Open</button></td></tr>)}</tbody></table></div>
 </section>
}
