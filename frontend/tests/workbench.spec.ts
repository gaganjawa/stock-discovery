import {test,expect} from '@playwright/test'
import {filterRows,type Row} from '../src/ResearchWorkbench'
const row=(symbol:string,rank:number,eligible:boolean):Row=>({listing_id:symbol,symbol,name:symbol==='A'?'Alpha Limited':'Beta Limited',state:'readable',reasons:[],screening:{swing:{ranking_eligible:eligible,rank,missing:[],assessment:{action:'INSUFFICIENT_EVIDENCE',reasons:[]}}},detail:{symbol,cutoff_at:'2026-01-03',price_series:[{time:'2026-01-02',close:'15',fetched_at:'2026-01-03',adjustment_basis:'split_bonus_adjusted'}],adjusted_research:{provider_id:'fixture',price_basis:'split_bonus_adjusted',metrics:{ema10:'12',ema30:'10',sma20:'11'},freshness:{status:'delayed_one_session',latest_verified_closed_session:'2026-01-03'}},financial_facts:[],publication_blockers:[]}})
test('search, stale and technical filters retain eligibility and never rank raw prices',()=>{
 const rows=[row('A',1,false),row('B',2,true),{...row('C',3,false),state:'denied',detail:undefined}]
 expect(filterRows(rows,'Alpha','all','all','symbol','swing').map(r=>r.symbol)).toEqual(['A'])
 expect(filterRows(rows,'','stale','ema_above','priority','swing').map(r=>r.symbol)).toEqual(['B','A'])
 expect(filterRows([{...row('D',4,false),state:'unavailable',detail:{...row('D',4,false).detail!,price_series:[]}}],'','stale','all','symbol','swing')).toHaveLength(0)
 expect(filterRows(rows,'','unavailable','all','symbol','swing').map(r=>r.symbol)).toEqual(['C'])
 expect(filterRows(rows,'','all','sma_above','symbol','swing')).toHaveLength(2)
})
test('comparison exposes differing dates, unavailable evidence and revocation clears values',async({page})=>{
 let denied=false
 await page.route('**/api/v1/dashboard',r=>r.fulfill({json:{datasets:[],jobs:[]}}))
 await page.route('**/v1/real-research/**',r=>r.fulfill({status:503,json:{detail:'Fixture unavailable'}}))
 await page.route('**/api/v1/session',r=>r.fulfill({json:{authenticated:true}}))
 await page.route('**/v1/real-research/workbench',r=>r.fulfill({json:{rows:denied?[{...row('A',1,false),state:'denied',detail:undefined,reasons:['source_permission_denied']}]:[row('A',1,false),{...row('B',2,false),state:'unavailable',detail:undefined,reasons:['session_coverage_unavailable']}]}}))
 await page.route('**/v1/real-research/watchlist',r=>r.fulfill({json:{entries:{}}}))
 await page.goto('/#real-research')
 const w=page.getByRole('region',{name:'Research workbench',exact:true})
 await w.getByLabel('Compare A',{exact:true}).check();await w.getByLabel('Compare B',{exact:true}).check()
 await w.getByRole('button',{name:'Compare (2/4)',exact:true}).click()
 const c=w.getByRole('region',{name:'Company comparison'})
 await expect(c).toContainText('2026-01-02');await expect(c).toContainText('No price date')
 await expect(w.locator('tbody')).toContainText('Not rankable')
 denied=true;await w.getByRole('button',{name:'Refresh stored evidence'}).click()
 await expect(w.locator('tbody')).toContainText('denied');await expect(w.locator('tbody')).not.toContainText('2026-01-02')
})
