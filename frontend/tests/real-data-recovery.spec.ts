import {test,expect} from '@playwright/test'
// STK-074/079 scripted UI fixtures only; no real company, price or provider data.
const status=(database:object,readiness:object)=>({blockers:['Database migration required: fixture'],publication_blockers:[],providers:[],models:{note:'Synthetic UI fixture'},scheduler:{prices:'blocked'},forward_paper:{reason:'blocked'},limitations:[],database,readiness})
for(const width of [1280,390])test('unmigrated database is explained instead of a permission denial '+width,async({page})=>{
 await page.setViewportSize({width,height:900})
 await page.route('**/api/v1/session',r=>r.fulfill({json:{authenticated:true}}))
 await page.route('**/api/v1/dashboard',r=>r.fulfill({json:{datasets:[],jobs:[]}}))
 await page.route('**/v1/real-research/status',r=>r.fulfill({json:status({state:'migration_required'},{level:'none',today:['Browse the synthetic workflows.'],next:['Level 1: permitted adjusted prices.']})}))
 await page.route('**/v1/real-research/scan',r=>r.fulfill({status:503,json:{detail:'not configured'}}))
 await page.route('**/v1/real-research/coverage',r=>r.fulfill({status:503,json:{detail:'Database migration required: fixture detail'}}))
 await page.route('**/v1/real-research/companies',r=>r.fulfill({json:{listing_ids:['NSE:TEST']}}))
 await page.route('**/v1/real-research/companies/NSE%3ATEST*',r=>r.fulfill({status:503,json:{detail:'Database migration required: the retained schema is older than this application, so permitted reads fail closed. No data was read or changed.'}}))
 await page.goto('/#real-research')
 await expect(page.getByTestId('database-migration-required')).toContainText('must be upgraded before permitted real data can be read')
 const banner=page.getByTestId('readiness-banner')
 await expect(banner).toContainText('No real-data level reached')
 await expect(banner).toContainText('Level 1: permitted adjusted prices.')
 await expect(page.getByTestId('pilot-coverage-error')).toContainText('Database migration required')
 const company=page.getByRole('region',{name:'Observed company research'})
 await expect(company.getByRole('alert')).toContainText('Database migration required')
 await expect(page.getByText('Source permission denied')).toHaveCount(0)
})

for(const width of [1280,390])test('pilot coverage explains each company and opens it '+width,async({page})=>{
 await page.setViewportSize({width,height:900})
 await page.route('**/api/v1/session',r=>r.fulfill({json:{authenticated:true}}))
 await page.route('**/api/v1/dashboard',r=>r.fulfill({json:{datasets:[],jobs:[]}}))
 await page.route('**/v1/real-research/status',r=>r.fulfill({json:status({state:'current'},{level:'level_1_descriptive',today:['Inspect permitted charts.'],next:['Level 2']})}))
 await page.route('**/v1/real-research/scan',r=>r.fulfill({status:503,json:{detail:'not configured'}}))
 await page.route('**/v1/real-research/companies',r=>r.fulfill({json:{listing_ids:['NSE:UIA','NSE:UIB']}}))
 let opened=''
 await page.route('**/v1/real-research/companies/*',r=>{opened=decodeURIComponent(new URL(r.request().url()).pathname.split('/').pop()??'');return r.fulfill({status:403,json:{detail:'Source permission denied'}})})
 await page.route('**/v1/real-research/coverage',r=>r.fulfill({json:{available:1,total:2,actionable:false,qualified:false,execution_qualified:false,rows:[
  {listing_id:'NSE:UIA',symbol:'UIA',state:'available',reasons:[],sessions:37,last_session:'2026-10-23',indicators:['atr14','ema10','sma20']},
  {listing_id:'NSE:UIB',symbol:'UIB',state:'unavailable',reasons:['batch_identity_missing_or_ambiguous'],sessions:0,last_session:null,indicators:[]}]}}))
 await page.goto('/#real-research')
 const panel=page.getByTestId('pilot-coverage')
 await expect(panel).toContainText('1 of 2 companies readable (descriptive only)')
 await expect(page.getByTestId('pilot-row-NSE:UIA')).toContainText('37 sessions to 2026-10-23 · atr14, ema10, sma20')
 await expect(page.getByTestId('pilot-row-NSE:UIB')).toContainText('the multi-stream rule is not approved')
 await page.getByTestId('pilot-open-NSE:UIB').click()
 await expect.poll(()=>opened).toBe('NSE:UIB')
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
})

test('corporate actions show ex-dates and never imply ratio arithmetic',async({page})=>{
 await page.setViewportSize({width:390,height:844})
 await page.route('**/api/v1/session',r=>r.fulfill({json:{authenticated:true}}))
 await page.route('**/api/v1/dashboard',r=>r.fulfill({json:{datasets:[],jobs:[]}}))
 await page.route('**/v1/real-research/status',r=>r.fulfill({json:status({state:'current'},{level:'none',today:[],next:[]})}))
 await page.route('**/v1/real-research/scan',r=>r.fulfill({status:503,json:{detail:'not configured'}}))
 await page.route('**/v1/real-research/coverage',r=>r.fulfill({status:503,json:{detail:'not configured'}}))
 await page.route('**/v1/real-research/companies',r=>r.fulfill({json:{listing_ids:['NSE:UIA']}}))
 await page.route('**/v1/real-research/companies/*',r=>r.fulfill({json:{symbol:'UIA',isin:'TEST',cutoff_at:'2026-10-31T10:00:00Z',price_series:[],financial_facts:[],documents:[],events:[],quantitative:{},limitations:[],analysis_history:[],
  corporate_actions:[{action_id:'upstox:dividend:2026-08-14:final',type:'dividend',effective_at:'2026-08-13T18:30:00Z',cash_per_share:'6',currency:'INR',observed_at:'2026-10-21T12:00:00Z'},
   {action_id:'upstox:bonus:2018-07-02:1:1',type:'unsupported',effective_at:'2018-07-01T18:30:00Z',cash_per_share:null,currency:'INR',observed_at:'2026-10-21T12:00:00Z'}]}}))
 await page.goto('/#real-research')
 const actions=page.getByTestId('corporate-actions')
 await expect(actions).toContainText('2026-08-14 · Dividend ₹6 per share (final) · observed 2026-10-21')
 await expect(actions).toContainText('2018-07-02 · Bonus 1:1 · ratio not used for adjustment')
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
})
