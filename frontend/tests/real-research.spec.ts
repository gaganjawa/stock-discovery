import {test,expect} from '@playwright/test'

test('real research never renders synthetic values and remains separate from forward paper',async({page})=>{
 const token=process.env.AUTH_TOKEN
 if(!token)throw new Error('Set the local test owner key')
 await page.goto('/#real-research')
 await page.getByLabel('Owner access key').fill(token)
 await page.getByRole('button',{name:'Sign in',exact:true}).click()
 await expect(page.getByRole('region',{name:'Real research',exact:true})).toBeVisible()
 await page.getByRole('link',{name:'Real research',exact:true}).click()
 const section=page.getByRole('region',{name:'Real research',exact:true})
 await expect(section).toContainText('Qualification and publication gates')
 await expect(section).toContainText('Exact publication blockers')
 await expect(section).toContainText('real policies required')
 await expect(section).toContainText('Real filing and event coverage requires source-specific acceptance.')
 for(const name of ['Swing','Short-term','Long-term']){
  await section.getByRole('tab',{name:new RegExp(name)}).click()
  await expect(section).toContainText('Only permitted records appear above.')
 }
 await expect(section).not.toContainText('SYN-D309')
 await expect(section).not.toContainText('₹')
 await expect(section).toContainText('Existing D3-10 admission gates remain in force')
 await page.screenshot({path:'test-results/real-research-blocked.png',fullPage:true})
 await page.getByRole('button',{name:'Sign out',exact:true}).click()
 await expect(section).toHaveCount(0)
 expect((await page.request.get('/v1/real-research/status')).status()).toBe(401)
})

// Fabricated HTTP responses test UI rendering/revocation only, not real integration.
test('configured evidence renders and permission denial removes cached company data',async({page})=>{
 await page.route('**/v1/real-research/companies',route=>route.fulfill({json:{listing_ids:['NSE:UI-TEST']}}))
 await page.route('**/v1/real-research/companies/NSE%3AUI-TEST',route=>route.fulfill({json:{symbol:'UI-TEST',isin:'TEST-ONLY',cutoff_at:'2026-10-19T12:00:00Z',
  price_series:[{time:'2026-10-16',open:'100',high:'110',low:'90',close:'105',volume:100}],
  financial_facts:[{fact_id:'test',metric:'revenue',value:'10000000',unit:'INR',period_end_at:'2026-03-31',scope:'consolidated',source_locator:'test page 3'}],
  market_readiness:{observed_bars:1,required_sessions:30,latest_verified_session:'2026-10-19T10:00:00Z',latest_bar:'2026-10-16T10:00:00Z',missing_sessions:['2026-10-19T10:00:00Z'],unverified_bar_sessions:[],warmup_complete:false,latest_session_present:false,within_proposed_age:false,volume_basis:'unverified',corporate_actions:'coverage_unverified',historical_pit:'unqualified'},policy_states:{swing:{ref:{id:'UI-PROPOSED',version:'test'},status:'unconfigured',approval_ref:null}},
  documents:[{title:'Fabricated browser-test filing',revision:{data:{url:'https://www.sec.gov/Archives/edgar/data/test.htm'},published_at:'2026-06-15T00:00:00Z'}}],events:[],
  quantitative:{swing:{action:'INSUFFICIENT_EVIDENCE',reasons:['policy_not_configured'],metrics:{}}},analysis_history:[{run_id:'UI-FACTUAL',horizon:'swing',cutoff_at:'2026-10-19T12:00:00Z',citations:[],result:{status:'completed',factual_report:{label:'VALIDATED FACTUAL RESEARCH',candidates:[],accepted_claims:[{text:'Fabricated historical test finding',citations:[],validation:'exact_fact_and_citation_passed'}],interpretive_findings:[],pending_interpretations:[],rejected_claims:[{kind:'interpretation',claim:{text:'Fabricated unsafe conclusion'},reason:'unsupported_quality_materiality_or_reconciliation_claim'}],limitations:['Fixture cash reconciliation conflict'],validation:{numerical:'passed',citations:'passed',semantic:'not_evaluated',recommendation:'unqualified'},source_observations:{}}}}],recommendations:[{recommendation:{recommendation_id:'UI-ONLY',action:'INSUFFICIENT_EVIDENCE',decision_available_at:'2026-10-20T12:00:00Z',information_cutoff_at:'2026-10-19T12:00:00Z',horizon:{profile:'swing'},rationale:{summary:'Fabricated browser publication'},missing_evidence:[{requirement:'rights',reason:'TEST missing input'}]},tracking:{status:'pending_future_observation',outcomes:[]}}],limitations:['Browser fixture only']}}))
 await page.goto('/')
 await page.getByLabel('Owner access key').fill(process.env.AUTH_TOKEN!)
 await page.getByRole('button',{name:'Sign in',exact:true}).click()
 await page.getByRole('link',{name:'Real research',exact:true}).click()
 const section=page.getByRole('region',{name:'Observed company research'})
 await expect(section).toContainText('UI-TEST · TEST-ONLY')
 await expect(section).toContainText('1,00,00,000 INR')
 await expect(section.getByLabel('Daily candlestick chart, 1 observed candles')).toBeVisible()
 await expect(section).toContainText('REAL RESEARCH / SHADOW / NON-ACTIONABLE')
 await expect(section).toContainText('Published 2026-10-20T12:00:00Z')
 await expect(section).toContainText('pending future observation')
 await expect(section).toContainText('No portfolio position or simulated fill')
 await expect(section).toContainText('RESEARCH-ONLY ASSESSMENT')
 await expect(section).toContainText('Warm-up incomplete.')
 await expect(section).toContainText('approval not granted')
 await expect(section).toContainText('VALIDATED FACTUAL RESEARCH')
 await expect(section).toContainText('NOT AN ACTIONABLE RECOMMENDATION')
 await expect(section).toContainText('Fabricated historical test finding')
 await expect(section).toContainText('Fixture cash reconciliation conflict')
 await section.getByText('Rejected model statements (1)',{exact:true}).click()
 await expect(section).toContainText('Rejected — Fabricated unsafe conclusion')
 await page.route('**/v1/real-research/companies/NSE%3AUI-TEST',route=>route.fulfill({status:403,json:{detail:'denied'}}))
 await section.getByRole('button',{name:'Refresh real evidence'}).click()
 await expect(section.getByRole('alert')).toContainText('Source permission denied')
 await expect(section).not.toContainText('1,00,00,000 INR')
 await expect(section.locator('canvas')).toHaveCount(0)
 await expect(section).not.toContainText('Fabricated historical test finding')
})

// Fabricated response exercises new scan rendering and revocation, not genuine scanning.
test('real homepage shows scan failures separately and clears cached scan on permission denial',async({page})=>{
 const row={listing_id:'NSE:SCAN-TEST',symbol:'SCAN-TEST',name:'Fictional UI-only identity',status:'stale',errors:['income-statement:tax_reconciliation'],financial_fact_count:0,research:{status:'not_selected'},screening:{swing:{rank:null,score:null,ranking_eligible:false,ranking_basis:[],missing:['latest_closed_session_missing'],assessment:{action:'INSUFFICIENT_EVIDENCE',reasons:['policy_not_configured']}}}}
 await page.route('**/v1/real-research/scan',route=>route.fulfill({json:{operations:{status:'stale_or_stopped',calendar_through:'2026-11-07',next_occurrence_at:'2026-10-26T10:30:00Z'},status:'observed',queue_depth:1,jobs:[],scan:{universe:{label:'LIMITED RESEARCH WATCHLIST',selection:'Fabricated UI fixture only',version:'test',members:[{symbol:row.symbol}]},completed_at:'2026-10-23T10:40:00Z',started_at:'2026-10-23T10:39:00Z',attempt:1,duration_seconds:60,api_requests:0,counts:{total:1,observed:0,stale:1,failed:0},rows:[row],publication:'blocked'}}}))
 await page.setExtraHTTPHeaders({Authorization:'Bearer '+process.env.AUTH_TOKEN!})
 await page.goto('/')
 const scan=page.getByRole('region',{name:'Automated real stock discovery'})
 await expect(scan).toContainText('LIMITED RESEARCH WATCHLIST')
 await expect(scan).toContainText('Not rankable')
 await expect(scan).toContainText('tax reconciliation')
 await expect(scan).toContainText('Worker: stale or stopped')
 await expect(scan).toContainText('Calendar verified through 2026-11-07')
 await expect(scan).toContainText('INSUFFICIENT EVIDENCE')
 await page.route('**/v1/real-research/scan',route=>route.fulfill({status:403,json:{detail:'Source permission denied'}}))
 await scan.getByRole('button',{name:'Refresh scan status'}).click()
 await expect(scan.getByRole('alert')).toContainText('Source permission denied')
 await expect(scan).not.toContainText('SCAN-TEST')
})
