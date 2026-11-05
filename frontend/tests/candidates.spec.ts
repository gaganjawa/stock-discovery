import {test,expect} from '@playwright/test'

test('candidate alerts stay partial, missing delivery stays unknown, unresolved symbols can be saved',async({page})=>{
 let saved=false
 await page.route('**/api/v1/session',r=>r.fulfill({json:{authenticated:true}}))
 await page.route('**/api/v1/dashboard',r=>r.fulfill({json:{datasets:[],jobs:[]}}))
 await page.route('**/v1/real-research/**',r=>r.fulfill({status:503,json:{detail:'Test evidence unavailable'}}))
 await page.route('**/v1/real-research/workbench',r=>r.fulfill({json:{rows:[]}}))
 await page.route('**/v1/real-research/watchlist**',r=>{
  if(r.request().method()==='PUT')saved=true
  return r.fulfill({json:{entries:saved?{'CHARTINK:test:TEST':{status:'Researching',note:''}}:{}}})
 })
 await page.route('**/v1/real-research/candidates?*',r=>r.fulfill({json:{rows:[{candidate_id:'fixture',watchlist_key:'CHARTINK:test:TEST',symbol:'TEST',session_date:'2026-11-05',scanner:{scan_name:'Synthetic scanner',version:'1'},source_url:'https://chartink.com',match_status:'first_observed_unverified',completeness:'partial_unverified',timestamp_basis:'receipt_date_unverified_provider_time_only',mode:'synthetic_fixture',research_status:'blocked',research:{status:'blocked',identity_status:'unverified',reasons:['nse_identity_missing_or_ambiguous'],research_priority:'not_rankable'}}],total:1,session_date:'2026-11-05',delivery_status:'observed_partial_or_snapshot',inbox:{completed:1}}}))
 await page.goto('/#real-research')
 const w=page.getByRole('region',{name:'Research workbench',exact:true})
 await w.getByRole('button',{name:'Candidates',exact:true}).click()
 const c=w.getByRole('region',{name:'Scanner candidates'})
 await expect(c).toContainText('partial unverified')
 await expect(c).toContainText('SYNTHETIC FIXTURE')
 await expect(c).toContainText('first observed unverified')
 await expect(c.getByRole('button',{name:'Open TEST research'})).toHaveCount(0)
 await c.getByRole('button',{name:'Save TEST to watchlist'}).click()
 await expect(c).toContainText('Saved to watchlist')
 await expect(w.getByRole('button',{name:'Watchlist (1)'})).toBeVisible()
})
