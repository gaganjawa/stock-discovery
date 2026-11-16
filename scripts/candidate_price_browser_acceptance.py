"""Real UI/API acceptance over the refresh test's disposable PostgreSQL database."""
from chartink_browser_acceptance import verify as browser


def verify(app, *, continuity=False):
    extra=r"""
await c.getByRole('button',{name:'Open INFY research',exact:true}).click();
const detail=p.getByRole('region',{name:'Observed company research',exact:true});
await expect(detail).toContainText('2026-10-20');
await expect(detail).toContainText('41');
await c.getByRole('button',{name:'Save INFY to watchlist',exact:true}).click();
await expect(c).toContainText('Saved to watchlist');
const work=p.getByRole('region',{name:'Research workbench',exact:true});
await work.getByRole('button',{name:/^Watchlist \(/}).click();
await expect(work).toContainText('INFY');
await expect(work).toContainText('readable');
await expect(work).toContainText('EMA10 equal EMA30');
await work.getByRole('button',{name:'Mark observations reviewed',exact:true}).click();
await expect(work).toContainText('Stored price observations marked reviewed');
console.log('PASS rolling candidate refresh -> open research -> saved watchlist continuity');
""" if continuity else ""
    script="""
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
const qualification=c.getByLabel('Qualification for INFY');
await expect(qualification).toContainText('permitted stored research');
await expect(qualification).toContainText('eligible stored research');
await expect(qualification).toContainText('current stored review');
await expect(qualification).toContainText('signal unqualified');
await expect(review).toContainText('relative volume: Unavailable');
await expect(c).toContainText('not a full-universe ranking or a BUY signal');
console.log('PASS candidate refresh -> stored analysis -> actual ranked UI');
__CONTINUITY__
}finally{await b.close()}})().catch(e=>{console.error(e);process.exit(1)});
"""
    browser(app,script=script.replace("__CONTINUITY__",extra))
