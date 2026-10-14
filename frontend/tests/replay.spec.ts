import { test, expect } from '@playwright/test'
import { readFileSync, existsSync } from 'node:fs'
const token=process.env.AUTH_TOKEN??(existsSync('../.env')?readFileSync('../.env','utf8').split('\n').find(x=>x.startsWith('AUTH_TOKEN='))?.slice(11):undefined)
test('authenticated synthetic freeze, reveal, scorecard and future placeholders',async({page})=>{
 if(!token)throw new Error('Set the local test access key; never use a broker credential')
 await page.goto('/')
 await page.getByLabel('Owner access key').fill(token)
 await page.getByRole('button',{name:'Sign in',exact:true}).click()
 await expect(page.getByRole('button',{name:'Sign out'})).toBeVisible()
 const initialize=page.getByRole('button',{name:'Load synthetic history'})
 if(await initialize.count())await initialize.click()
 await expect(page.getByRole('heading',{name:'Fictional history is ready'})).toBeVisible({timeout:60000})
 await page.getByRole('link',{name:'Replay',exact:true}).click()
 const date=await page.getByLabel('Historical date').inputValue()
 const response=page.waitForResponse(r=>r.url().endsWith('/api/v1/analysis')&&r.request().method()==='POST')
 await page.getByRole('button',{name:'Freeze recommendation'}).click()
 const frozen=await (await response).json()
 expect(frozen.candles.length).toBe(40)
 expect(frozen.candles.every((b:{time:string})=>b.time<=date)).toBeTruthy()
 expect(frozen.trade).toBeUndefined()
 await page.getByRole('button',{name:'Explain recommendation',exact:true}).click()
 await expect(page.getByRole('heading',{name:'Rule-based explanation',exact:true})).toBeVisible()
 await expect(page.getByRole('region',{name:'Recommendation explanation',exact:true})).toContainText(frozen.recommendation.rationale.summary)
 await expect(page.getByLabel('Strategy',{exact:true})).toHaveValue(frozen.recommendation.strategy.version)
 const card=page.locator('section').filter({has:page.getByRole('heading',{name:'Frozen rule results'})})
 for(const value of [frozen.recommendation.rationale.summary,frozen.recommendation.rationale.invalidation,frozen.recommendation.strategy.version,frozen.recommendation.strategy.config_version,frozen.recommendation.versions.dataset,frozen.recommendation.versions.code,frozen.recommendation.information_cutoff_at]) await expect(card).toContainText(value)
 await expect(card).not.toContainText(/confidence|probability/i)
 await expect(page.getByRole('heading',{name:'Prices known at the cutoff'})).toBeVisible()
 await expect(page.locator('canvas').first()).toBeVisible()
 const attribution=page.locator('.attribution')
 await expect(attribution).toBeVisible()
 await expect(attribution.getByRole('link',{name:'TradingView',exact:true})).toHaveAttribute('href','https://www.tradingview.com/')
 await expect(attribution).toContainText('Copyright © 2025 TradingView, Inc.')
 const noticesLink=attribution.getByRole('link',{name:'Third-party licences'})
 await expect(noticesLink).toBeVisible()
 const notices=await page.request.get((await noticesLink.getAttribute('href'))!)
 expect(notices.ok()).toBeTruthy()
 const noticeText=await notices.text()
 for(const text of ['Apache License','Version 2.0','react 19.1.1','fancy-canvas','Permission is hereby granted','Microsoft Corporation']) expect(noticeText).toContain(text)
 // A chart ResizeObserver must not grow its own host or move the reveal control.
 const layout=await page.locator('.candle-chart').evaluate(async host=>{
  const button=host.parentElement!.querySelector('button')!;
  const samples=[];
  for(let i=0;i<6;i++){
   await new Promise<void>(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>resolve())));
   samples.push({height:host.getBoundingClientRect().height,y:button.getBoundingClientRect().top+window.scrollY});
  }
  return {samples,tableMargin:getComputedStyle(host.querySelector('table')!).marginTop};
 });
 expect(layout.tableMargin).toBe('0px');
 expect(layout.samples.every(s=>Math.abs(s.height-340)<1)).toBeTruthy();
 expect(Math.max(...layout.samples.map(s=>s.y))-Math.min(...layout.samples.map(s=>s.y))).toBeLessThan(1);
 const revealResponse=page.waitForResponse(r=>r.url().endsWith('/reveal'))
 await page.getByRole('button',{name:'Reveal future prices and outcome'}).click()
 const revealed=await (await revealResponse).json()
 expect(revealed.candles.some((b:{time:string})=>b.time>date)).toBeTruthy()
 await expect(page.getByRole('heading',{name:'Subsequent prices revealed'})).toBeVisible()
 await page.screenshot({path:'test-results/replay.png',fullPage:true})
 const dates=await page.getByLabel('Historical date').locator('option').evaluateAll(options=>options.map(o=>(o as HTMLOptionElement).value))
 await page.getByLabel('Historical date').selectOption(dates.find(d=>d!==date)!)
 await expect(page.getByRole('heading',{name:'Subsequent prices revealed'})).toHaveCount(0)
 await expect(page.getByRole('heading',{name:'Frozen rule results'})).toHaveCount(0)
 const nextFreeze=page.waitForResponse(r=>r.url().endsWith('/api/v1/analysis')&&r.request().method()==='POST')
 await page.getByRole('button',{name:'Freeze recommendation'}).click()
 await nextFreeze
 await expect(page.getByRole('heading',{name:'Prices known at the cutoff'})).toBeVisible()
 const instruments=await page.getByLabel('Instrument',{exact:true}).locator('option').evaluateAll(options=>options.map(o=>(o as HTMLOptionElement).value))
 await page.getByLabel('Instrument',{exact:true}).selectOption(instruments[1])
 await expect(page.getByRole('heading',{name:'Frozen rule results'})).toHaveCount(0)
 await expect(page.locator('canvas')).toHaveCount(0)
 await page.getByRole('link',{name:'Scorecard',exact:true}).click()
 await expect(page.getByText('Directional accuracy',{exact:true})).toBeVisible()
 const groups=page.getByLabel('Evaluation version group',{exact:true})
 const chosenGroup=await groups.locator('option').nth(1).getAttribute('value')
 const groupResponse=page.waitForResponse(r=>r.url().includes('/api/v1/scorecard?cohort='))
 await groups.selectOption(chosenGroup!)
 const selectedScores=await (await groupResponse).json()
 expect(selectedScores.selected_cohort).toBe(chosenGroup)
 const chronology=page.getByRole('region',{name:'Chronological split audit',exact:true})
 await expect(chronology).toContainText('never realized profits')
 await expect(chronology).toContainText(selectedScores.chronological_validation.audit_id)
 await expect(chronology).toContainText(selectedScores.chronological_validation.limitation)
 const assigned=Object.values(selectedScores.chronological_validation.windows).flatMap((w:any)=>w.recommendation_ids)
 expect(new Set([...assigned,...selectedScores.chronological_validation.exclusions.map((e:any)=>e.id)]).size).toBe(selectedScores.eligibility.length)
 for(const [name,window] of Object.entries(selectedScores.chronological_validation.windows) as [string,any][]){
  const row=chronology.getByRole('row').filter({has:page.getByRole('rowheader',{name,exact:true})})
  await expect(row.getByRole('cell').nth(0)).toHaveText(window.start_at)
  await expect(row.getByRole('cell').nth(1)).toHaveText(window.end_at)
  await expect(row.getByRole('cell').nth(2)).toHaveText(String(window.recommendation_ids.length))
 }
 const validation=page.getByRole('region',{name:'Validation report',exact:true})
 await expect(validation).toContainText('not the probability of a future recommendation succeeding')
 await expect(validation).toContainText('do not add their sample counts together')
 for(const limitation of selectedScores.validation_report.limitations)await expect(validation).toContainText(limitation)
 for(const [name,group] of Object.entries(selectedScores.validation_report.groups) as [string,any][]){
  const row=validation.getByRole('row').filter({has:page.getByRole('rowheader',{name:name.replaceAll('_',' '),exact:true})})
  await expect(row.getByRole('cell').nth(0)).toHaveText(String(group.sample_count))
  await expect(row.getByRole('cell').nth(1)).toHaveText(String(group.metrics.direction.denominator))
  const interval=group.direction_interval
  if(interval.lower===null)await expect(row.getByRole('cell').nth(3)).toContainText('Not available')
  else{
   await expect(row.getByRole('cell').nth(3)).toContainText(Number(interval.lower).toLocaleString('en-IN',{maximumFractionDigits:4})+' to '+Number(interval.upper).toLocaleString('en-IN',{maximumFractionDigits:4}))
   await expect(row.getByRole('cell').nth(3)).toContainText(interval.method)
  }
 }
 for(const [label,counts] of [['Recommendation counts',selectedScores.action_counts],['Trade outcome counts',selectedScores.trade_status_counts]] as const){
  const section=page.getByRole('region',{name:label,exact:true})
  await expect(section).toBeVisible()
  expect(Object.values(counts).reduce((sum:any,value:any)=>sum+value,0)).toBe(selectedScores.eligibility.length)
  for(const [name,count] of Object.entries(counts)){
   const row=section.locator('dl > div').filter({has:page.getByText(name.replaceAll('_',' '),{exact:true})})
   await expect(row.locator('dd')).toHaveText(String(count))
  }
 }
 const activity=page.getByRole('region',{name:'Portfolio activity',exact:true})
 await expect(activity).toContainText('not a turnover percentage')
 for(const [label,key] of [['Traded notional ₹','turnover_notional_inr'],['Closing-mark exposure fraction','exposure_mark_fraction']]){
  const value=selectedScores.portfolio[key]
  const expected=value===undefined?'Not available':Number(value).toLocaleString('en-IN',{maximumFractionDigits:4})
  await expect(activity.locator('dl > div').filter({has:page.getByText(label,{exact:true})}).locator('dd')).toHaveText(expected)
 }
 if(selectedScores.portfolio.exposure_definition)await expect(activity).toContainText(selectedScores.portfolio.exposure_definition)
 await expect(groups).toHaveValue(chosenGroup!)
 await page.getByRole('button',{name:'Refresh scorecard',exact:true}).click()
 await expect(groups).toHaveValue(chosenGroup!)
 const batchResponse=page.waitForResponse(r=>r.url().endsWith('/api/v1/experiments')&&r.request().method()==='POST')
 await page.getByRole('button',{name:'Run synthetic sample batch'}).click()
 const batch=await (await batchResponse).json()
 expect(batch.job_ids).toHaveLength(9)
 await expect.poll(async()=>{
  const jobs=await Promise.all(batch.job_ids.map(async(id:string)=>(await page.request.get('/api/v1/jobs/'+id)).json()))
  return jobs.every(j=>j.status==='completed')
 },{timeout:60000}).toBeTruthy()
 await page.getByRole('button',{name:/Inspect job/}).first().click()
 await expect(page.getByRole('heading',{name:'Job details'})).toBeVisible()
 await page.getByRole('link',{name:'Scorecard',exact:true}).click()
 const downloadEvent=page.waitForEvent('download')
 await page.getByRole('button',{name:'Export audit JSON'}).click()
 const download=await downloadEvent
 const audit=JSON.parse(readFileSync((await download.path())!,'utf8'))
 for(const id of batch.job_ids){
  const job=audit.jobs.find((j:{job_id:string})=>j.job_id===id)
  expect(job.status).toBe('completed')
  expect(job.payload.code_version).toBe(frozen.recommendation.versions.code)
  expect(job.payload.strategy_version).toBe(frozen.recommendation.strategy.version)
  expect(job.payload.config_version).toBe(frozen.recommendation.strategy.config_version)
  for(const rid of job.result.recommendation_ids){
   const decision=audit.decisions.find((d:{recommendation_id:string})=>d.recommendation_id===rid)
   expect(decision.run_id).toBeTruthy()
   expect(audit.runs.some((r:any)=>r.analysis.recommendation.run_id===decision.run_id)).toBeTruthy()
   expect(audit.outcomes.some((o:any)=>o.recommendation_id===rid)).toBeTruthy()
  }
 }
 await page.getByRole('link',{name:'Portfolio',exact:true}).click()
 await expect(page.getByRole('heading',{name:'Planned for a future release'})).toBeVisible()
 await page.getByRole('button',{name:'Sign out'}).click()
 await expect(page.getByLabel('Owner access key')).toBeVisible()
})
