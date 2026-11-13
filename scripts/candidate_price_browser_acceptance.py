"""Real UI/API acceptance over the refresh test's disposable PostgreSQL database."""
from chartink_browser_acceptance import verify as browser


def verify(app):
    browser(app,script="""
const {chromium,expect}=require(process.env.STK_PLAYWRIGHT);
(async()=>{const b=await chromium.launch();try{const p=await b.newPage();
await p.goto(process.env.STK_URL+'/#real-research');
await p.getByLabel('Owner access key').fill('o'.repeat(40));
await p.getByRole('button',{name:'Sign in',exact:true}).click();
await p.getByRole('region',{name:'Research workbench',exact:true}).getByRole('button',{name:'Candidates',exact:true}).click();
const c=p.getByRole('region',{name:'Scanner candidates'});
await expect(c).toContainText('INFY');await expect(c).toContainText('41 bars');
await expect(c.getByLabel('Price refresh for INFY')).toContainText('Price refresh: completed');
await c.getByRole('checkbox',{name:'Review stored swing prices'}).check();
const review=c.getByLabel('Swing price review for INFY');
await expect(review).toContainText('Page research rank 1');
await expect(review).toContainText('relative volume: Unavailable');
await expect(c).toContainText('not a full-universe ranking or a BUY signal');
console.log('PASS candidate refresh -> stored analysis -> actual ranked UI');
}finally{await b.close()}})().catch(e=>{console.error(e);process.exit(1)});
""")
