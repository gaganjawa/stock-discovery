import {test,expect} from '@playwright/test'

test('real research never renders synthetic values and remains separate from forward paper',async({page})=>{
 const token=process.env.AUTH_TOKEN
 if(!token)throw new Error('Set the local test owner key')
 await page.goto('/')
 await page.getByLabel('Owner access key').fill(token)
 await page.getByRole('button',{name:'Sign in',exact:true}).click()
 await page.getByRole('link',{name:'Real research',exact:true}).click()
 const section=page.getByRole('region',{name:'Real research',exact:true})
 await expect(section).toContainText('Qualification and publication gates')
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
  documents:[{title:'Fabricated browser-test filing',revision:{data:{url:'https://www.sec.gov/Archives/edgar/data/test.htm'},published_at:'2026-06-15T00:00:00Z'}}],events:[],
  quantitative:{swing:{action:'INSUFFICIENT_EVIDENCE',reasons:['policy_not_configured'],metrics:{}}},analysis_history:[],recommendations:[{recommendation:{recommendation_id:'UI-ONLY',action:'INSUFFICIENT_EVIDENCE',decision_available_at:'2026-10-20T12:00:00Z',information_cutoff_at:'2026-10-19T12:00:00Z',horizon:{profile:'swing'},rationale:{summary:'Fabricated browser publication'},missing_evidence:[{requirement:'rights',reason:'TEST missing input'}]},tracking:{status:'pending_future_observation',outcomes:[]}}],limitations:['Browser fixture only']}}))
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
 await page.route('**/v1/real-research/companies/NSE%3AUI-TEST',route=>route.fulfill({status:403,json:{detail:'denied'}}))
 await section.getByRole('button',{name:'Refresh real evidence'}).click()
 await expect(section.getByRole('alert')).toContainText('Source permission denied')
 await expect(section).not.toContainText('1,00,00,000 INR')
 await expect(section.locator('canvas')).toHaveCount(0)
})
