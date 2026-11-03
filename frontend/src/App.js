import "@/App.css";
import { ASSESSMENT, BLOCKERS, TIMELINE, DECISIONS, NEXT, TODAY, CHANGES, RUNBOOK } from "@/handoff";

const Section = ({ id, kicker, title, children }) => (
  <section className="sec" id={id} data-testid={`section-${id}`}>
    <p className="kicker">{kicker}</p>
    <h2>{title}</h2>
    {children}
  </section>
);

const Hero = () => (
  <header className="hero" data-testid="hero">
    <p className="kicker">Stock Discovery · takeover audit · 3 Nov 2026</p>
    <h1>The INFY 403 is a schema gap, not a permission problem.</h1>
    <p className="lede">
      The retained database is at migration 0013. The read fences arrive in 0015, so every permitted read fails closed.
      A second, independent blocker: 13 rolling price streams can't qualify as one batch. Both now have a tested path. Nothing
      on your Mac, GitHub or any provider was touched.
    </p>
    <div className="pills">
      <span className="pill ok" data-testid="pill-pr35">PR #35 · 4/4 CI green · 0 reviews</span>
      <span className="pill warn" data-testid="pill-db">Retained DB 0013 → needs 0015</span>
      <span className="pill" data-testid="pill-level">Today: no real-data level reached</span>
    </div>
  </header>
);

const Table = ({ rows, cols, testid }) => (
  <div className="tablewrap"><table data-testid={testid}>
    <thead><tr>{cols.map(c => <th key={c}>{c}</th>)}</tr></thead>
    <tbody>{rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j}>{c}</td>)}</tr>)}</tbody>
  </table></div>
);

const Shots = () => (
  <div className="shots">
    {[["before_migration.png", "Simulated retained 0013 database: the app now says “Database migration required” instead of “Source permission denied”."],
      ["chart.png", "Same data after the copy-only rehearsal, with the multi-stream rule approved: chart and descriptive indicators return."]]
      .map(([src, cap]) => (
        <figure key={src} data-testid={`shot-${src.split(".")[0]}`}>
          <a href={`/handoff/${src}`} target="_blank" rel="noreferrer"><img src={`/handoff/${src}`} alt={cap} /></a>
          <figcaption>{cap} Invented rows only.</figcaption>
        </figure>
      ))}
  </div>
);

const List = ({ items, ordered, testid }) => {
  const Tag = ordered ? "ol" : "ul";
  return <Tag className="list" data-testid={testid}>{items.map(t => <li key={t}>{t}</li>)}</Tag>;
};

export default function App() {
  return (
    <main className="page">
      <Hero />
      <Section id="assessment" kicker="A" title="Where the project actually stands">
        <Table testid="assessment-table" cols={["Area", "State", "Basis"]} rows={ASSESSMENT} />
      </Section>
      <Section id="changes" kicker="Delivered" title="What this branch adds">
        <List items={CHANGES} testid="changes-list" />
        <Shots />
        <a className="btn" href="/handoff/stk-079-recovery.patch" download data-testid="download-patch">Download patch (on top of PR #35)</a>
        <a className="btn ghost" href="/handoff/STK-079-takeover-audit.md" download data-testid="download-audit">Download full audit</a>
      </Section>
      <Section id="runbook" kicker="Your next step" title="Run on your Mac (read-only on the original)">
        <List items={RUNBOOK} ordered testid="runbook-list" />
      </Section>
      <Section id="blockers" kicker="C" title="Critical blockers">
        <Table testid="blockers-table" cols={["#", "Blocker", "Fix alone?", "Your action", "Cost / time"]} rows={BLOCKERS} />
      </Section>
      <Section id="timeline" kicker="D" title="Realistic timeline">
        <Table testid="timeline-table" cols={["Milestone", "Target", "Gate"]} rows={TIMELINE} />
      </Section>
      <Section id="today" kicker="What you can do" title="Today, and after each milestone">
        <Table testid="today-table" cols={["When", "You can"]} rows={TODAY} />
      </Section>
      <Section id="decisions" kicker="Approvals" title="Decisions only you can make">
        <List items={DECISIONS} ordered testid="decisions-list" />
      </Section>
      <Section id="next" kicker="E" title="Next three tasks">
        <List items={NEXT} ordered testid="next-list" />
      </Section>
      <footer className="foot">Costs today: ₹0/month. Kite ₹500/month and Hetzner about €5–7/month are optional. The NSE licence price is unknown until quoted.</footer>
    </main>
  );
}
