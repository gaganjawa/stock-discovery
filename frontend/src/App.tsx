import { useEffect, useState } from 'react'
const pages = [
 ['dashboard','Dashboard','◫','Your research workspace, at a glance.','Your workspace is ready','No saved research, replay results or holdings yet. Explore a section to see what belongs here.'],
 ['research','Research','⌕','Evidence and context for companies you follow.','No research saved yet','Company evidence, fundamentals and technical context will appear here. No market sources are connected.'],
 ['replay','Replay','↺','Evaluate frozen decisions against subsequent observations.','No replay results yet','Forecast outcomes and simulated trade results will be shown separately. Historical evaluation is not available yet.'],
 ['portfolio','Portfolio','▤','Holdings, contributions and trading capital in one place.','No holdings connected','Contributions, active trading capital and long-term investments will be tracked separately. No real balances are connected.'],
 ['ipo','IPO','↗','Research companies coming to market.','No IPO research yet','Offer documents and evidence-led assessments will appear here. No live offerings are loaded.'],
] as const
const selected = () => pages.find(p => window.location.hash === `#${p[0]}`) ?? pages[0]
export function App() {
 const [page,setPage] = useState(selected)
 const [demo,setDemo] = useState(false)
 useEffect(() => { const navigate = () => {setPage(selected());setDemo(false)}; window.addEventListener('hashchange',navigate); return () => window.removeEventListener('hashchange',navigate) },[])
 useEffect(() => {document.title = `${page[1]} · Stock Discovery`},[page])
 return <div className="workspace"><a className="skip" href="#content" onClick={event => { event.preventDefault(); document.getElementById("content")?.focus() }}>Skip to content</a>
 <aside><a className="brand" href="#dashboard"><b>sd↗</b><span>Stock Discovery<small>PRIVATE RESEARCH</small></span></a><p className="nav-label">WORKSPACE</p>
 <nav aria-label="Main navigation">{pages.map(p => <a key={p[0]} href={`#${p[0]}`} aria-current={page[0] === p[0] ? 'page' : undefined}><span aria-hidden="true">{p[2]}</span>{p[1]}</a>)}</nav><div className="side-note">● Local workspace<p>Private by design.<br/>Built for considered decisions.</p></div></aside>
 <div className="body"><header>Workspace <span>/</span> <strong>{page[1]}</strong><span className="badge">PREVIEW</span></header>
 <main id="content" tabIndex={-1}><p className="eyebrow">YOUR RESEARCH, IN FOCUS</p><h1>{page[1]}</h1><p className="subtitle">{page[3]}</p>
 <div className="notice"><strong>A preview of your workspace.</strong> Demo content is fictional. No live prices, account balances or actionable recommendations are shown.</div>
 <section className="hero"><div><p className="eyebrow">A PLACE TO BEGIN</p><h2>Start with a question.<br/>Build a clearer view.</h2><p>Good research starts with evidence.<br/>Your workspace will grow as you build it.</p></div><div className="art" aria-hidden="true">{[40,65,55,100,85,130].map((height,i) => <i key={i} style={{height}}/>)}</div></section>
 <section className="panel" aria-labelledby="state-heading"><div className="panel-head"><h2 id="state-heading">{page[1]} workspace</h2><button aria-pressed={demo} onClick={() => setDemo(!demo)}>{demo ? 'Show empty state' : 'View fictional example'}</button></div>
 {demo ? <div className="demo" role="status"><span className="badge">FICTIONAL EXAMPLE</span><h3>{page[1]} · Example Company</h3><p>This sample shows where {page[1].toLowerCase()} content will appear. No evidence has been collected and no analysis has been run.</p><dl><div><dt>Data source</dt><dd>Synthetic display example</dd></div><div><dt>Recommendation</dt><dd>None</dd></div><div><dt>{page[0] === 'portfolio' ? 'Account value' : 'Evaluation'}</dt><dd>Not available</dd></div></dl></div> : <div className="empty"><span className="empty-icon" aria-hidden="true">{page[2]}</span><h3>{page[4]}</h3><p>{page[5]}</p><button className="primary" onClick={() => setDemo(true)}>Explore a fictional example →</button></div>}
 </section>
 {page[0] === 'dashboard' && <section className="tiles" aria-label="Explore your workspace">{pages.slice(1).map(p => <a href={`#${p[0]}`} key={p[0]}><span aria-hidden="true">{p[2]}</span><h3>{p[1]} ↗</h3><p>{p[3]}</p></a>)}</section>}
 <footer>Stock Discovery · Private Indian equity research <span>Synthetic preview · No orders enabled</span></footer></main></div></div>
}
