import {test,expect} from './fixtures/authenticated'
import {readFileSync} from 'node:fs'
import {createHash} from 'node:crypto'
const template=JSON.parse(readFileSync(new URL('./fixtures/governance.json',import.meta.url),'utf8'))
const canonical=(v:any):any=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v
const hash=(v:any)=>createHash('sha256').update(JSON.stringify(canonical(v))).digest('hex')

test('Discovery opens its own frozen history, reveals only recorded outcomes and navigates to exact registered evidence',async({page})=>{
 test.setTimeout(180000)
 await page.goto('/#dashboard')
 await expect(page.getByRole('button',{name:'Sign out',exact:true})).toBeVisible()
 const origin=new URL(page.url()).origin
 async function post(path:string,data:any,key=crypto.randomUUID()){
  const response=await page.request.post('/v1'+path,{headers:{Origin:origin,'Idempotency-Key':key},data})
  expect(response.ok(),await response.text()).toBe(true);return response.json()
 }
 async function run(){const r=await post('/discovery-runs',{horizon:'swing'});await expect.poll(async()=>{
  const value=await (await page.request.get('/v1/runs/'+r.run_id)).json();return value.status
 },{timeout:60000}).toBe('completed');return r.run_id}
 const oldRun=await run()
 const old=await (await page.request.get('/v1/discovery?cohort=quant_rag&batch_id='+oldRun)).json()
 const oldRid=old.recommendations.find((r:any)=>r.instrument.symbol==='SYN-D309-READY').recommendation_id
 const currentRun=await run()
 const current=await (await page.request.get('/v1/discovery?cohort=quant_rag&batch_id='+currentRun)).json()
 const rec=current.recommendations.find((r:any)=>r.instrument.symbol==='SYN-D309-READY'),rid=rec.recommendation_id
 const pid=(await post('/paper-portfolio',{name:'Navigation browser fixture',mode:'fictional_simulation',contract_version:'fictional-simulation-1.0.0',starting_capital:'100000',simulation_start_at:'2025-06-25T10:01:01Z'})).portfolio_id
 await post(`/paper-portfolio/${pid}/admissions`,{recommendation_id:rid})
 await post(`/paper-portfolio/${pid}/fictional-session`,{})
 await expect.poll(async()=>((await (await page.request.get('/v1/paper-portfolio/'+pid)).json()).pending_observations),{timeout:30000}).toBe(0)
 const comparisons=await (await page.request.get('/v1/recommendations/'+rid+'/comparisons')).json()
 const artifacts=await Promise.all(comparisons.recommendations.map(async(r:any)=>(await page.request.get('/v1/recommendations/'+r.recommendation_id)).json()))
 const eid='SYN-NAV-'+crypto.randomUUID(),tid='TRIAL-NAV-'+crypto.randomUUID()
 const experiment={...template,experiment_id:eid,universe:[rec.instrument.instrument_id],universe_ref:{...template.universe_ref,content_hash:hash([rec.instrument.instrument_id])},
  validation:{start:'2025-01-01T00:00:00Z',end:'2031-12-31T00:00:00Z'},test:{start:'2040-01-01T00:00:00Z',end:'2047-01-01T00:00:00Z'},
  samples:[{sample_id:'SYN-navigation',listing_id:rec.instrument.instrument_id,cutoff:rec.information_cutoff_at,label_end:rec.horizon.holding_end_at,groups:['SYN-navigation'],input_hash:hash(artifacts[0].input_manifest),revision_ids:[]}],
  embargo_seconds:Math.ceil((Date.parse(rec.horizon.holding_end_at)-Date.parse(rec.information_cutoff_at))/1000),
  arms:template.arms.map((a:any)=>{const x=artifacts.find((x:any)=>x.recommendation.cohort.arm===a.arm),research=x.research,bundle=x.research_bundle
   return {...a,strategy_hash:hash(x.policy_manifest),policy_hash:hash(x.recommendation.policy_refs),cost_hash:hash(x.recommendation.policy_refs.cost),risk_hash:hash(x.recommendation.policy_refs.risk),
    model_hash:research?.model?hash(research.model):a.model_hash,retrieval_hash:bundle?.ranking?hash({ranking:bundle.ranking,embedding:bundle.embedding??null}):a.retrieval_hash,
    prompt_hash:research?.agent_prompt_hash||research?.prompt_hash?hash(research.agent_prompt_hash??research.prompt_hash):a.prompt_hash}
  })}
 await post('/experiments',experiment,eid)
 await post('/experiments/'+eid+'/trials',{trial_id:tid,experiment_id:eid,split:'validation',outcome_cutoff:'2031-12-31T00:00:00Z',arms:artifacts.map((a:any)=>({arm:a.recommendation.cohort.arm,publication_run_id:currentRun,recommendation_ids:[a.recommendation.recommendation_id]}))},tid)
 let writes=0
 page.on('request',r=>{if(r.method()==='POST')writes++})
 const discovery=page.getByRole('region',{name:'Three-horizon discovery'}),detail=discovery.getByRole('region',{name:'Discovery recommendation details'})
 await discovery.getByLabel('Discovery research mode').selectOption('quant_rag')
 await discovery.getByRole('button',{name:'Refresh discovery'}).click()
 await discovery.getByRole('button',{name:'Inspect SYN-D309-READY',exact:true}).click()
 await expect(detail).toContainText(rec.information_cutoff_at)
 await expect(detail.getByRole('heading',{name:'Citations and sources',exact:true})).toBeVisible()
 await detail.getByRole('button',{name:'Inspect source 1',exact:true}).click()
 await expect(detail.getByRole('region',{name:'Source inspection'})).toContainText('Fictional')
 const saved=detail.getByRole('region',{name:'Discovery saved evidence'})
 await saved.getByRole('button',{name:'Open saved historical evidence',exact:true}).click()
 await expect(saved).toContainText('Legacy Replay unavailable')
 await expect(saved.getByRole('region',{name:'Recorded discovery outcome'})).toHaveCount(0)
 await saved.getByRole('button',{name:'Reveal recorded outcome '+pid,exact:true}).click()
 await expect(saved.getByRole('region',{name:'Recorded discovery outcome'})).toContainText('Pinned ledger #')
 await saved.getByText('Recorded recommendation history',{exact:true}).click()
 await expect(saved).toContainText('admission')
 await saved.getByRole('button',{name:'Inspect frozen recommendation '+oldRid,exact:true}).click()
 await expect(detail).toContainText(oldRid)
 await saved.getByRole('button',{name:'Open saved historical evidence',exact:true}).click()
 await expect(saved).toContainText('Outcome unavailable: no recorded ledger relates')
 await expect(saved).toContainText('Evaluation unavailable: no registered trial references')
 await saved.getByRole('button',{name:'Inspect frozen recommendation '+rid,exact:true}).click()
 await saved.getByRole('button',{name:'Open saved historical evidence',exact:true}).click()
 await saved.getByRole('button',{name:'View registered evaluation '+eid,exact:true}).click()
 await expect(page.getByRole('heading',{name:'Scorecard',exact:true})).toBeVisible()
 const folds=page.getByRole('region',{name:'Registered fold results',exact:true})
 await expect(folds.getByRole('checkbox',{name:'Report folds '+eid,exact:true})).toBeChecked()
 await folds.getByRole('button',{name:'Read registered fold results',exact:true}).click()
 await expect(folds).toContainText(tid)
 await expect(folds).toContainText('Not evaluated; this read will not evaluate it')
 expect(writes).toBe(0)
 const trial=await (await page.request.get('/v1/experiments/'+eid)).json()
 expect(trial.trials.find((t:any)=>t.trial_id===tid).result).toBeNull()
 await page.getByRole('link',{name:'Dashboard',exact:true}).click()
 await discovery.getByLabel('Discovery research mode').selectOption('quant_rag')
 await discovery.getByRole('button',{name:'Inspect SYN-D309-READY',exact:true}).click()
 await saved.getByRole('button',{name:'Open saved historical evidence',exact:true}).click()
 await page.route('**/v1/paper-portfolio/*/outcomes/*?*',r=>r.fulfill({status:403,json:{detail:'PRIVATE MUST NOT RENDER'}}))
 await saved.getByRole('button',{name:'Reveal recorded outcome '+pid,exact:true}).click()
 await expect(detail).toHaveCount(0)
 await expect(discovery.getByRole('region',{name:'Stock comparison'})).toHaveCount(0)
 await expect(discovery).toContainText('Saved evidence is restricted')
 await expect(page.getByText('PRIVATE MUST NOT RENDER')).toHaveCount(0)
 expect(writes).toBe(0)
})
