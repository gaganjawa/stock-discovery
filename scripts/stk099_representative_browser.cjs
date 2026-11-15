// STK-099: actual restored UI over a private SSH tunnel. No API mocking or writes.
const fs=require('fs');const {chromium,expect}=require(process.env.STK_PLAYWRIGHT);
(async()=>{const browser=await chromium.launch();try{
 const page=await browser.newPage({ignoreHTTPSErrors:true,httpCredentials:{username:'owner',password:fs.readFileSync(process.env.STK_EDGE_PASSWORD_FILE,'utf8').trim()}});
 page.on('pageerror',e=>console.log('PAGE_ERROR',e.message));
 page.on('response',async r=>{const path=new URL(r.url()).pathname;if(r.status()>=400)console.log('HTTP',r.status(),path);if(path.endsWith('/watchlist')&&r.ok())console.log('WATCHLIST_COUNT',Object.keys((await r.json()).entries??{}).length);if(path.endsWith('/workbench')&&r.ok())console.log('WORKBENCH_ROWS',(await r.json()).rows?.length)});
 await page.goto(process.env.STK_URL+'/#real-research');
 await page.getByLabel('Owner access key').fill(fs.readFileSync(process.env.STK_OWNER_KEY_FILE,'utf8').trim());
 await page.getByRole('button',{name:'Sign in',exact:true}).click();
 const workbench=page.getByRole('region',{name:'Research workbench',exact:true});
 await expect(workbench).toBeVisible();
 await workbench.getByRole('button',{name:/Watchlist \(/}).click();
 await expect(workbench.getByRole('button',{name:/Watchlist \([1-9]/})).toBeVisible({timeout:60000});
 await workbench.getByRole('button',{name:'Candidates',exact:true}).click();
 await expect(workbench.getByRole('region',{name:'Scanner candidates'})).toBeVisible();
 console.log('PASS restored authenticated UI, existing watchlist and Candidates view; no write or market acceptance');
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exit(1)});
