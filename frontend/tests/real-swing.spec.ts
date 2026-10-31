import {test,expect} from '@playwright/test'
// UI-only synthetic responses; this does not establish real-data acceptance.
for(const viewport of [{width:1280,height:800},{width:390,height:844}])test('stored swing analysis clears obsolete evidence '+viewport.width,async({page})=>{
 await page.setViewportSize(viewport)
 await page.route('**/api/v1/session',r=>r.fulfill({json:{authenticated:true}}))
 await page.route('**/api/v1/dashboard',r=>r.fulfill({json:{datasets:[],jobs:[]}}))
 await page.route('**/v1/real-research/status',r=>r.fulfill({json:{blockers:[],publication_blockers:[],providers:[],models:{note:'Synthetic browser fixture'},scheduler:{prices:'blocked'},forward_paper:{reason:'blocked'},limitations:[]}}))
 await page.route('**/v1/real-research/scan',r=>r.fulfill({status:503,json:{detail:'not configured'}}))
 await page.route('**/v1/real-research/companies',r=>r.fulfill({json:{listing_ids:['NSE:UI-TEST']}}))
 let denied=false,forbidden=false
 const requested:string[]=[]
 await page.route('**/v1/real-research/companies/NSE%3AUI-TEST*',r=>{
  const url=new URL(r.request().url())
  if(url.searchParams.get('analysis')!=='swing')return r.fulfill({json:{symbol:'UI-TEST',isin:'TEST',cutoff_at:'2026-10-31T10:00:00Z',price_series:[],financial_facts:[],documents:[],events:[],quantitative:{},limitations:['Synthetic browser fixture'],analysis_history:[{run_id:'UI-ONLY',cutoff_at:'2026-10-31T10:00:00Z',horizon:'swing',citations:[],result:{status:'completed',factual_report:{label:'NO VALIDATED FACTUAL CLAIMS',candidates:[],accepted_claims:[],accepted_source_excerpts:[{text:'Synthetic quoted source statement',citations:[],validation:'exact_source_excerpt_only'}],pending_interpretations:[],rejected_claims:[],limitations:['News coverage is unknown'],source_observations:{},validation:{numerical:'no_accepted_claims',citations:'no_accepted_claims',semantic:'not_evaluated',recommendation:'unqualified'}}}}]}})
  requested.push(url.searchParams.get('cutoff_at')??'current')
  if(forbidden)return r.fulfill({status:403,json:{detail:'PRIVATE SERVER DETAIL MUST NOT RENDER'}})
  return r.fulfill(denied?{json:{instrument_id:'NSE:UI-TEST',status:'INSUFFICIENT_EVIDENCE',analysis_cutoff_at:'2026-10-31T10:00:00Z',reasons:['source_access_or_provenance_unavailable'],indicators:{},levels:null,hypothetical_sizing:null,evidence_revisions:[],analysis_id:null}}:{json:{instrument_id:'NSE:UI-TEST',status:'BUY',analysis_cutoff_at:'2026-10-31T10:00:00Z',reasons:['technical_conditions_met'],indicators:{atr14:'2.50'},levels:{entry:'100.00',stop:'95.00',entry_cap:'101.00',target:'110.00'},hypothetical_sizing:{quantity:10,planned_loss:'65.00',entry_cash:'1012.00',scenario_only:true},evidence_revisions:['UI-REVISION-ONLY'],analysis_id:'UI-ANALYSIS',formula_version:'test',strategy_version:'test',policy_version:'test'}})
 })
 await page.goto('/#real-research')
 const swing=page.getByRole('region',{name:'Technical swing research',exact:true})
 await expect(swing).toBeVisible()
 const excerpts=page.getByRole('region',{name:'Attributed source excerpts'})
 await expect(excerpts).toContainText('Synthetic quoted source statement')
 await expect(excerpts).toContainText('not independently verified')
 expect(requested).toEqual([]) // No automatic inference/acquisition or analysis.
 await swing.getByRole('button',{name:'Analyze stored swing evidence'}).click()
 await expect(swing).toContainText('Scenario quantity: 10')
 await expect(swing).toContainText('Research only')
 await expect(swing).toContainText('UI-REVISION-ONLY')
 await swing.getByLabel('Analysis cutoff (UTC, optional)').fill('2026-10-30T10:00:00Z')
 await expect(swing).not.toContainText('Scenario quantity')
 await expect(swing).not.toContainText('UI-REVISION-ONLY')
 denied=true
 await swing.getByRole('button',{name:'Analyze stored swing evidence'}).click()
 await expect(swing).toContainText('INSUFFICIENT EVIDENCE')
 await expect(swing).not.toContainText('101.00')
 expect(requested).toEqual(['current','2026-10-30T10:00:00Z'])
 forbidden=true
 await swing.getByRole('button',{name:'Analyze stored swing evidence'}).click()
 await expect(swing.getByRole('alert')).toHaveText('Source permission denied.')
 await expect(swing).not.toContainText('UI-REVISION-ONLY')
 await expect(page.getByText('PRIVATE SERVER DETAIL MUST NOT RENDER')).toHaveCount(0)
 await page.getByRole('tab',{name:/Short-term/}).click()
 await expect(swing).toHaveCount(0)
})
