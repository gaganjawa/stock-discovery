// STK-099 synthetic localhost-only HTTPS browser acceptance; no API mocks.
const {chromium, expect} = require(process.env.STK_PLAYWRIGHT);
(async () => {
  const target = new URL(process.env.STK_URL);
  if (target.hostname !== 'localhost' || target.protocol !== 'https:') throw Error('Local synthetic HTTPS only');
  const browser = await chromium.launch();
  try {
    const context = await browser.newContext({ignoreHTTPSErrors: true,
      httpCredentials: {username: 'owner', password: process.env.STK_EDGE_PASSWORD},
      extraHTTPHeaders: {Authorization: 'Basic ' + Buffer.from('owner:' + process.env.STK_EDGE_PASSWORD).toString('base64')}});
    const page = await context.newPage();
    page.on('requestfailed', request => console.error('Hosted browser request failed:', new URL(request.url()).pathname, request.failure()?.errorText));
    await page.goto(target.origin + '/#real-research');
    await page.getByLabel('Owner access key').fill('o'.repeat(40));
    await page.getByRole('button', {name: 'Sign in', exact: true}).click();
    await page.getByRole('region', {name: 'Research workbench', exact: true})
      .getByRole('button', {name: 'Candidates', exact: true}).click();
    const candidates = page.getByRole('region', {name: 'Scanner candidates'});
    await expect(candidates).toContainText('SYN097');
    await expect(candidates).toContainText('SYNTHETIC FIXTURE');
    await candidates.getByRole('button', {name: 'Save SYN097 to watchlist', exact: true}).click();
    await expect(candidates).toContainText('Saved to watchlist');
    await page.reload();
    const cookies = await context.cookies();
    const session = cookies.find(c => c.name === 'stk_session');
    if (!session?.secure || !session?.httpOnly || session.sameSite !== 'Strict') throw Error('Unsafe session cookie');
    console.log('PASS: authenticated HTTPS UI, candidate, watchlist and secure cookie');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
