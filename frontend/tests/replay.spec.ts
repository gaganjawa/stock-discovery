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
 await expect(page.getByRole('heading',{name:'Prices known at the cutoff'})).toBeVisible()
 await expect(page.locator('canvas').first()).toBeVisible()
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
 await page.getByRole('button',{name:'Reveal future prices and outcome'}).click()
 await expect(page.getByRole('heading',{name:'Subsequent prices revealed'})).toBeVisible()
 await page.screenshot({path:'test-results/replay.png',fullPage:true})
 await page.getByRole('link',{name:'Scorecard',exact:true}).click()
 await expect(page.getByText('Directional accuracy',{exact:true})).toBeVisible()
 await page.getByRole('link',{name:'Portfolio',exact:true}).click()
 await expect(page.getByRole('heading',{name:'Planned for a future release'})).toBeVisible()
 await page.getByRole('button',{name:'Sign out'}).click()
 await expect(page.getByLabel('Owner access key')).toBeVisible()
})
