import {test as base,expect,type APIRequestContext} from '@playwright/test'
import {readFileSync,existsSync} from 'node:fs'
type State=Awaited<ReturnType<APIRequestContext['storageState']>>
// One real login per worker; each test still receives a separate browser context.
// Replay retains the UI sign-in test. Do not weaken the server's five/minute gate.
export const test=base.extend<{}, {ownerState:State}>({
 ownerState:[async({playwright},use)=>{
  const token=process.env.AUTH_TOKEN??(existsSync('../.env')?readFileSync('../.env','utf8').split('\n').find(x=>x.startsWith('AUTH_TOKEN='))?.slice(11):undefined)
  if(!token)throw Error('Set the disposable test owner key')
  const api=await playwright.request.newContext({baseURL:process.env.STK_BROWSER_BASE_URL??'http://127.0.0.1:5173'})
  try{
   const response=await api.post('/api/v1/session',{data:{token}})
   expect(response.status(),'Test-session authentication failed').toBe(200)
   const state=await api.storageState()
   expect(state.cookies.some(c=>c.name==='stk_session'&&c.httpOnly)).toBeTruthy()
   await use(state)
  }finally{await api.dispose()}
 },{scope:'worker'}],
 storageState:async({ownerState},use)=>{await use(ownerState)},
})
export {expect}
