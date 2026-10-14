export type ChronologicalData={status:string;audit_id?:string;reason?:string;policy?:string;limitation?:string;gap_sessions?:number;maximum_label_sessions?:number;windows?:Record<string,{start_at:string;end_at:string;recommendation_ids:string[]}>;exclusions?:{id:string;reason:string}[]}
export function ChronologicalReport({report}:{report:ChronologicalData}){
 return <section aria-label="Chronological split audit"><h3>Chronological split audit</h3>
 {report.status==='unavailable'?<p>{report.reason?.replaceAll('_',' ')}</p>:<>
 <p>{report.limitation}</p><p>Audit ID: {report.audit_id}</p><p>Boundary gap: {report.gap_sessions} sessions. Reserved label window: {report.maximum_label_sessions} future sessions for every action.</p>
 <p>Assignments use frozen dates and configuration, never realized profits. This audit does not filter the overall scorecard or run a training experiment.</p>
 <div className="table-wrap"><table><thead><tr><th>Window</th><th>Starts (UTC)</th><th>Ends (UTC)</th><th>Retained recommendations</th></tr></thead><tbody>{Object.entries(report.windows??{}).map(([name,window])=><tr key={name}><th scope="row">{name}</th><td>{window.start_at}</td><td>{window.end_at}</td><td>{window.recommendation_ids.length}</td></tr>)}</tbody></table></div>
 <details><summary>Split assignments and exclusions</summary>{Object.entries(report.windows??{}).map(([name,window])=><p key={name}>{name}: {window.recommendation_ids.join(', ')||'None'}</p>)}{report.exclusions?.map(e=><p key={e.id}>{e.id}: {e.reason.replaceAll('_',' ')}</p>)}</details>
 </>}</section>
}
