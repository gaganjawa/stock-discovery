import {test,expect} from '@playwright/test'
// STK-074/079 scripted UI fixtures only; no real company, price or provider data.
const RULES={version:'1.0.0',decision_file:'absent',active:0,rules:[
 {id:3,section:'Scope',rule:'Real money',value:'None. Forward paper only, and no broker orders.',decision:'approve',state:'approved_inactive',waiting_on:[]},
 {id:15,section:'Horizon',rule:'Swing',value:'Swing 2.0.0',decision:'approve',state:'approved_inactive',waiting_on:['original_prices_qualified']},
 {id:23,section:'Benchmarks',rule:'Market benchmark',value:'NIFTY 500 TRI',decision:null,state:'proposed_not_decided',waiting_on:['owner_approval','benchmark_source_permitted']}]}
const status=(database:object,readiness:object)=>({blockers:['Database migration required: fixture'],publication_blockers:[],providers:[],models:{note:'Synthetic UI fixture'},scheduler:{prices:'blocked'},forward_paper:{reason:'blocked'},limitations:[],database,readiness})
for(const width of [1280,390])test('unmigrated database is explained instead of a permission denial '+width,async({page})=>{
 await page.setViewportSize({width,height:900})
 await page.route('**/api/v1/session',r=>r.fulfill({json:{authenticated:true}}))
 await page.route('**/api/v1/dashboard',r=>r.fulfill({json:{datasets:[],jobs:[]}}))
 await page.route('**/v1/real-research/status',r=>r.fulfill({json:status({state:'migration_required'},{level:'none',today:['Browse the synthetic workflows.'],next:['Level 1: permitted adjusted prices.']})}))
 await page.route('**/v1/real-research/scan',r=>r.fulfill({status:503,json:{detail:'not configured'}}))
 await page.route('**/v1/real-research/rules',r=>r.fulfill({json:RULES}))
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
 await page.route('**/v1/real-research/rules',r=>r.fulfill({json:RULES}))
 await page.route('**/v1/real-research/coverage',r=>r.fulfill({json:{available:1,total:2,actionable:false,qualified:false,execution_qualified:false,rows:[
  {listing_id:'NSE:UIA',symbol:'UIA',state:'available',reasons:[],sessions:37,last_session:'2026-10-23',indicators:['atr14','ema10','sma20'],refresh:{current:true,latest_session:'2026-10-23T10:00:00Z',latest_bar:'2026-10-23T10:00:00Z',missing_sessions:0}},
  {listing_id:'NSE:UIB',symbol:'UIB',state:'unavailable',reasons:['batch_identity_missing_or_ambiguous'],sessions:0,last_session:null,indicators:[],refresh:{current:false,latest_session:'2026-10-23T10:00:00Z',latest_bar:'2026-10-21T10:00:00Z',missing_sessions:2}},
  {listing_id:'NSE:UIC',state:'denied',reasons:['source_permission_denied']}]}}))
 await page.goto('/#real-research')
 const panel=page.getByTestId('pilot-coverage')
 await expect(panel).toContainText('1 of 3 companies readable (descriptive only)')
 await expect(page.getByTestId('daily-coverage-note')).toContainText('Daily note · latest verified session 2026-10-23 · prices current for 1 of 3 · charts readable for 1 of 3.')
 await expect(page.getByTestId('daily-note-stale')).toHaveText('Prices behind: UIB (last price 2026-10-21, 2 sessions missing).')
 await expect(page.getByTestId('daily-note-blocked')).toContainText('Chart not readable: UIB (Prices come from separate downloads without a verified common observation batch.); NSE:UIC (No current permitted grant covers this read.)')
 await expect(page.getByTestId('pilot-row-NSE:UIA')).toContainText('37 sessions to 2026-10-23 · atr14, ema10, sma20')
 await expect(page.getByTestId('pilot-row-NSE:UIB')).toContainText('without a verified common observation batch')
 await page.getByTestId('pilot-open-NSE:UIB').click()
 await expect.poll(()=>opened).toBe('NSE:UIB')
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
})

test('corporate actions show ex-dates and chart markers without ratio arithmetic',async({page})=>{
 await page.setViewportSize({width:390,height:844})
 await page.route('**/api/v1/session',r=>r.fulfill({json:{authenticated:true}}))
 await page.route('**/api/v1/dashboard',r=>r.fulfill({json:{datasets:[],jobs:[]}}))
 await page.route('**/v1/real-research/status',r=>r.fulfill({json:status({state:'current'},{level:'none',today:[],next:[]})}))
 await page.route('**/v1/real-research/scan',r=>r.fulfill({status:503,json:{detail:'not configured'}}))
 await page.route('**/v1/real-research/rules',r=>r.fulfill({json:RULES}))
 await page.route('**/v1/real-research/coverage',r=>r.fulfill({status:503,json:{detail:'not configured'}}))
 await page.route('**/v1/real-research/companies',r=>r.fulfill({json:{listing_ids:['NSE:UIA']}}))
 await page.route('**/v1/real-research/companies/*',r=>r.fulfill({json:{symbol:'UIA',isin:'TEST',cutoff_at:'2026-10-31T10:00:00Z',financial_facts:[],documents:[],events:[],quantitative:{},limitations:[],analysis_history:[],
  corporate_actions:[{action_id:'upstox:dividend:2026-08-14:final',type:'dividend',effective_at:'2026-08-13T18:30:00Z',cash_per_share:'6',currency:'INR',observed_at:'2026-10-21T12:00:00Z'},
   {action_id:'upstox:bonus:2018-07-02:1:1',type:'unsupported',effective_at:'2018-07-01T18:30:00Z',cash_per_share:null,currency:'INR',observed_at:'2026-10-21T12:00:00Z'},
   {action_id:'upstox:bonus:2026-08-15:1:1',type:'unsupported',effective_at:'2026-08-14T18:30:00Z',cash_per_share:null,currency:'INR',observed_at:'2026-10-21T12:00:00Z'}],
  price_series:[{time:'2026-08-13',open:'10',high:'11',low:'9',close:'10',volume:1},{time:'2026-08-14',open:'10',high:'11',low:'9',close:'10',volume:1},{time:'2026-08-17',open:'10',high:'11',low:'9',close:'10',volume:1}]}}))
 await page.goto('/#real-research')
 const actions=page.getByTestId('corporate-actions')
 await expect(actions).toContainText('2026-08-14 · Dividend ₹6 per share (final) · observed 2026-10-21')
 await expect(actions).toContainText('2018-07-02 · Bonus 1:1 · ratio not used for adjustment')
 // Markers: inside the plotted window only; a weekend ex-date is shown on the next session.
 const marks=page.getByTestId('chart-ex-dates')
 await expect(marks).toContainText('D 2026-08-14 · Dividend ₹6 per share (final)')
 await expect(marks).toContainText('B/S 2026-08-15 (shown on 2026-08-17) · Bonus 1:1 · ratio not used for adjustment')
 await expect(marks).not.toContainText('2018-07-02')
 await expect(page.getByLabel(/3 observed candles, 2 ex-date markers/)).toBeVisible()
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
})

test('starting rules show versions, decisions and what each still waits on',async({page})=>{
 await page.setViewportSize({width:390,height:844})
 await page.route('**/api/v1/session',r=>r.fulfill({json:{authenticated:true}}))
 await page.route('**/api/v1/dashboard',r=>r.fulfill({json:{datasets:[],jobs:[]}}))
 await page.route('**/v1/real-research/status',r=>r.fulfill({json:status({state:'current'},{level:'none',today:[],next:[]})}))
 await page.route('**/v1/real-research/scan',r=>r.fulfill({status:503,json:{detail:'not configured'}}))
 await page.route('**/v1/real-research/coverage',r=>r.fulfill({status:503,json:{detail:'not configured'}}))
 await page.route('**/v1/real-research/companies',r=>r.fulfill({json:{listing_ids:[]}}))
 await page.route('**/v1/real-research/rules',r=>r.fulfill({json:RULES}))
 await page.goto('/#real-research')
 const rules=page.getByTestId('owner-rules')
 await expect(rules).toContainText('Starting rules v1.0.0 · 2 of 3 approved · 0 active')
 await rules.locator('summary').click()
 await expect(page.getByTestId('owner-rule-3')).toContainText('Approved, inactive')
 await expect(page.getByTestId('owner-rule-15')).toContainText('original prices')
 await expect(page.getByTestId('owner-rule-23')).toContainText('your decision, benchmark data')
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
})

test('companies are named by symbol and unreadable reasons are explained',async({page})=>{
 await page.setViewportSize({width:390,height:844})
 await page.route('**/api/v1/session',r=>r.fulfill({json:{authenticated:true}}))
 await page.route('**/api/v1/dashboard',r=>r.fulfill({json:{datasets:[],jobs:[]}}))
 await page.route('**/v1/real-research/status',r=>r.fulfill({json:status({state:'current'},{level:'none',today:[],next:[]})}))
 await page.route('**/v1/real-research/scan',r=>r.fulfill({status:503,json:{detail:'not configured'}}))
 await page.route('**/v1/real-research/rules',r=>r.fulfill({json:RULES}))
 await page.route('**/v1/real-research/coverage',r=>r.fulfill({json:{available:0,total:2,rows:[
  {listing_id:'NSE:INE009A01021',symbol:'INFY',state:'unavailable',reasons:['batch_identity_missing_or_ambiguous'],sessions:0,last_session:null,indicators:[]},
  {listing_id:'NSE:UIZ',state:'unavailable',reasons:['unexpected_runtimeerror']}]}}))
 await page.route('**/v1/real-research/companies',r=>r.fulfill({json:{listing_ids:['NSE:INE009A01021','NSE:UIZ']}}))
 await page.route('**/v1/real-research/companies/*',r=>r.request().url().includes('UIZ')
  ?r.fulfill({status:403,json:{detail:'Source permission denied'}})
  :r.fulfill({status:503,json:{detail:'Real company inputs are unavailable: real_identity_missing_or_ambiguous'}}))
 await page.goto('/#real-research')
 const company=page.getByRole('region',{name:'Observed company research'})
 const select=company.locator('select').first()
 await expect(select.locator('option').first()).toHaveText('INFY · NSE:INE009A01021')
 await expect(page.getByTestId('company-isin-hint')).toBeVisible()
 await expect(company.getByRole('alert')).toHaveText('Real company inputs are unavailable: No single verified company identity is stored. (real_identity_missing_or_ambiguous)')
 await select.selectOption('NSE:UIZ')
 await expect(company.getByRole('alert')).toHaveText('Source permission denied')
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
})

test('a missing database file is explained instead of an internal failure',async({page})=>{
 await page.setViewportSize({width:390,height:844})
 const detail='Database connection file not found: check DATABASE_URL_FILE points to an existing file.'
 await page.route('**/api/v1/session',r=>r.fulfill({json:{authenticated:true}}))
 await page.route('**/api/v1/dashboard',r=>r.fulfill({status:503,json:{detail}}))
 await page.route('**/v1/real-research/status',r=>r.fulfill({json:status({state:'unavailable'},{level:'none',today:[],next:[]})}))
 await page.route('**/v1/real-research/scan',r=>r.fulfill({status:503,json:{detail}}))
 await page.route('**/v1/real-research/rules',r=>r.fulfill({json:RULES}))
 await page.route('**/v1/real-research/coverage',r=>r.fulfill({status:503,json:{detail}}))
 await page.route('**/v1/real-research/companies',r=>r.fulfill({json:{listing_ids:['NSE:INE009A01021']}}))
 await page.route('**/v1/real-research/companies/*',r=>r.fulfill({status:503,json:{detail}}))
 await page.goto('/#real-research')
 await expect(page.getByTestId('database-unreachable')).toContainText('DATABASE_URL_FILE')
 await expect(page.getByRole('region',{name:'Observed company research'}).getByRole('alert').first()).toHaveText(detail)
 await expect(page.getByText('Internal request failure')).toHaveCount(0)
})
