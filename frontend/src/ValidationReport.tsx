export type ValidationData={
 status:string;
 limitations:string[];
 groups:Record<string,{
  sample_count:number;
  metrics:{direction:{value:string|null;denominator:number}};
  direction_interval:{lower:string|null;upper:string|null;method?:string;reason?:string};
 }>;
}
const fraction=(value:string|null)=>value===null?'Not available':Number(value).toLocaleString('en-IN',{maximumFractionDigits:4})
export function ValidationReport({report}:{report:ValidationData}){
 return <section aria-label="Validation report">
  <h3>Validation report</h3>
  <p>Software validation only. These fictional results do not establish trading accuracy or profitability.</p>
  <p>Groups overlap across dimensions: do not add their sample counts together. Directional rates and intervals are fractions, not percentages.</p>
  <p>Intervals describe the observed sample, not the probability of a future recommendation succeeding. Overlapping trades can violate the independence assumption.</p>
  {report.limitations.map(item=><p key={item}>{item}</p>)}
  {Object.keys(report.groups).length===0?<p>No recommendations in this version group.</p>:<div className="table-wrap"><table>
   <thead><tr><th>Group</th><th>Recommendations</th><th>Eligible directional outcomes</th><th>Directional rate</th><th>95% descriptive interval</th></tr></thead>
   <tbody>{Object.entries(report.groups).map(([name,group])=>{
    const interval=group.direction_interval
    return <tr key={name}><th scope="row">{name.replaceAll('_',' ')}</th><td>{group.sample_count}</td><td>{group.metrics.direction.denominator}</td><td>{fraction(group.metrics.direction.value)}</td><td>{interval.lower===null||interval.upper===null?'Not available — '+(interval.reason??'insufficient evidence').replaceAll('_',' '):fraction(interval.lower)+' to '+fraction(interval.upper)}{interval.method&&<p>{interval.method}</p>}</td></tr>
   })}</tbody>
  </table></div>}
 </section>
}
