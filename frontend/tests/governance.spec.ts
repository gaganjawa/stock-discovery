import {test,expect} from '@playwright/test'
import {readFileSync,existsSync} from 'node:fs'
const manifest=JSON.parse(readFileSync(new URL('./fixtures/governance.json',import.meta.url),'utf8'))
const token=process.env.AUTH_TOKEN??(existsSync('../.env')?readFileSync('../.env','utf8').split('\n').find(x=>x.startsWith('AUTH_TOKEN='))?.slice(11):undefined)

test('immutable experiment registry, explicit unavailable outcomes and promotion blockers',async({page})=>{
 if(!token)throw new Error('Set the disposable test owner key')
 await page.goto('/')
 await page.getByLabel('Owner access key').fill(token)
 await page.getByRole('button',{name:'Sign in',exact:true}).click()
 await expect(page.getByRole('button',{name:'Sign out',exact:true})).toBeVisible()
 const origin=new URL(page.url()).origin
 const eid='SYN-BROWSER-'+crypto.randomUUID(),tid='TRIAL-'+crypto.randomUUID()
 let response=await page.request.post('/v1/experiments',{headers:{Origin:origin,'Idempotency-Key':eid},data:{...manifest,experiment_id:eid}})
 expect(response.status()).toBe(200)
 const trial={trial_id:tid,experiment_id:eid,split:'validation',outcome_cutoff:'2030-01-01T00:00:00Z',arms:['quant','quant_rag','quant_agent'].map(arm=>({arm,publication_run_id:null,recommendation_ids:[]}))}
 response=await page.request.post('/v1/experiments/'+eid+'/trials',{headers:{Origin:origin,'Idempotency-Key':tid},data:trial})
 expect(response.status()).toBe(200)
 response=await page.request.post(`/v1/experiments/${eid}/trials/${tid}/evaluate`,{headers:{Origin:origin,'Idempotency-Key':tid}})
 expect(response.status()).toBe(200)
 await page.getByRole('link',{name:'Scorecard',exact:true}).click()
 const region=page.getByRole('region',{name:'Experiment governance'})
 await expect(region).toContainText('Strategy promotion blocked')
 await region.getByRole('button',{name:eid,exact:true}).click()
 await expect(region).toContainText('Fixture safeguards, not investment research')
 await expect(region).toContainText('synthetic software only')
 await expect(region.getByRole('table')).toContainText('Unavailable')
 await region.getByText('Immutable trial history',{exact:true}).click()
 await expect(region).toContainText('trial completed')
 await page.route('**/v1/experiments',r=>r.fulfill({status:403,contentType:'application/json',body:'{}'}))
 await region.getByRole('button',{name:'Refresh experiments'}).click()
 await expect(region.getByRole('alert')).toContainText('Source permission denied')
 await expect(region.getByRole('region',{name:'Experiment details'})).toHaveCount(0)
})
