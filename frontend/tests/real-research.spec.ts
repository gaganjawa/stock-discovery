import {test,expect} from '@playwright/test'

test('real research never renders synthetic values and remains separate from forward paper',async({page})=>{
 const token=process.env.AUTH_TOKEN
 if(!token)throw new Error('Set the local test owner key')
 await page.goto('/')
 await page.getByLabel('Owner access key').fill(token)
 await page.getByRole('button',{name:'Sign in',exact:true}).click()
 await page.getByRole('link',{name:'Real research',exact:true}).click()
 const section=page.getByRole('region',{name:'Real research',exact:true})
 await expect(section).toContainText('Research unavailable')
 await expect(section).toContainText('No real-company financial statements or events have been ingested.')
 for(const name of ['Swing','Short-term','Long-term']){
  await section.getByRole('tab',{name:new RegExp(name)}).click()
  await expect(section).toContainText('No published research, price chart, entry conditions, targets or performance results')
 }
 await expect(section).not.toContainText('SYN-D309')
 await expect(section).not.toContainText('₹')
 await expect(section).toContainText('Existing D3-10 admission gates remain in force')
 await page.screenshot({path:'test-results/real-research-blocked.png',fullPage:true})
 await page.getByRole('button',{name:'Sign out',exact:true}).click()
 await expect(section).toHaveCount(0)
 expect((await page.request.get('/v1/real-research/status')).status()).toBe(401)
})
