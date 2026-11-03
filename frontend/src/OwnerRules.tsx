import { useEffect, useState } from 'react'

type RuleRow={id:number;section:string;rule:string;value:string;decision:string|null;state:string;waiting_on:string[]}
type Rules={version:string;decision_file:string;rules:RuleRow[];active:number}
const STATE:Record<string,string>={proposed_not_decided:'Proposed',deferred:'Deferred',approved_inactive:'Approved, inactive',eligible_for_activation:'Ready to activate'}
const GATE:Record<string,string>={owner_approval:'your decision',database_current:'database upgrade',forward_paper_authorized:'forward paper authorisation',
 original_prices_qualified:'original prices',filing_rights_and_timestamps:'filing rights',benchmark_source_permitted:'benchmark data',independent_ai_review:'50-case review'}

// STK-079: rules are shown with what each still waits on; this panel cannot activate anything.
export function OwnerRules({onUnauthorized}:{onUnauthorized:()=>void}) {
 const [data,setData]=useState<Rules|null>(null),[error,setError]=useState('')
 useEffect(()=>{let active=true
  fetch('/v1/real-research/rules').then(r=>{if(r.status===401)onUnauthorized();if(!r.ok)throw Error('Starting rules are unavailable.');return r.json()})
   .then(d=>{if(active)setData(d)}).catch(e=>{if(active)setError(e.message)})
  return()=>{active=false}},[])
 if(error)return <p role="alert" className="error" data-testid="owner-rules-error">{error}</p>
 if(!data)return null
 const approved=data.rules.filter(r=>r.decision==='approve'||r.decision==='change').length
 return <details className="panel" data-testid="owner-rules"><summary>Starting rules v{data.version} · {approved} of {data.rules.length} approved · {data.active} active</summary>
  {data.decision_file==='mismatched_version_ignored'&&<p role="alert" className="error" data-testid="owner-rules-mismatch">Your decision file is for a different rules version and was ignored.</p>}
  <div className="table-wrap"><table><thead><tr><th>#</th><th>Rule</th><th>Value</th><th>State</th><th>Waiting on</th></tr></thead><tbody>
   {data.rules.map(r=><tr key={r.id} data-testid={`owner-rule-${r.id}`}><td>{r.id}</td><td>{r.rule}</td><td>{r.value}</td><td>{STATE[r.state]??r.state}</td><td>{r.waiting_on.map(g=>GATE[g]??g).join(', ')||'nothing'}</td></tr>)}
  </tbody></table></div></details>
}
