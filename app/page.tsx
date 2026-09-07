import season from "@/data/parsed/seasons/2008.json";

const nav = ["Seasons", "What if?", "Greatest", "Matches", "Methods"];

export default function Home() {
  const leader = season.actual_table[0];
  const matches = season.matches.slice(0, 5);

  return (
    <main>
      <header className="site-header shell">
        <a className="wordmark" href="#top" aria-label="How Fluky Was the IPL home">
          HOW FLUKY<span>?</span>
        </a>
        <nav aria-label="Primary navigation">
          {nav.map((item) => <a href="#pipeline" key={item}>{item}</a>)}
        </nav>
        <div className="live-pill"><i /> Data lab · 01</div>
      </header>

      <section className="hero shell" id="top">
        <div className="eyebrow"><span>01</span> An IPL counterfactual</div>
        <h1>
          Was the best<br className="mobile-break" /> team
          <br className="desktop-break" />actually
          <br className="mobile-break" /> <em>the best?</em>
        </h1>
        <p className="dek">Every IPL season, replayed 10,000 times. Skill gets a rating. Luck gets a number.</p>
        <div className="hero-meta">
          <span>19 seasons</span><span>1,243 source matches</span><span>Match-level simulation</span>
        </div>
      </section>

      <section className="scoreboard" aria-label="2008 ingest status">
        <div className="shell score-grid">
          <div>
            <div className="eyebrow amber"><span>DATA 001</span> First innings</div>
            <h2>The archive<br />is talking.</h2>
            <p>{season.summary.matches} matches from the inaugural season are now normalised into one deterministic, simulation-ready file.</p>
          </div>
          <div className="stat-stack">
            <article><small>Season parsed</small><strong>2008</strong><b>Complete</b></article>
            <article><small>League fixtures</small><strong>{season.summary.league_matches}</strong><b>Verified</b></article>
            <article><small>Playoff fixtures</small><strong>{season.summary.playoff_matches}</strong><b>Verified</b></article>
          </div>
        </div>
      </section>

      <section className="table-section shell" id="pipeline">
        <div className="section-heading">
          <div><div className="eyebrow"><span>ACTUAL</span> Before the simulations</div><h2>2008, as played.</h2></div>
          <p><b>{leader.team.name}</b> set the benchmark at {leader.points} points. The model will soon ask how often they do it again.</p>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Pos</th><th>Team</th><th>P</th><th>W</th><th>L</th><th>NR</th><th>NRR</th><th>Pts</th></tr></thead>
            <tbody>
              {season.actual_table.map((row) => (
                <tr key={row.team.id}>
                  <td>{String(row.position).padStart(2, "0")}</td>
                  <td><span className={`team-dot team-${row.team.abbr.toLowerCase()}`} />{row.team.name}<small>{row.team.abbr}</small></td>
                  <td>{row.played}</td><td>{row.won}</td><td>{row.lost}</td><td>{row.no_result}</td>
                  <td>{row.net_run_rate > 0 ? "+" : ""}{row.net_run_rate.toFixed(3)}</td><td><b>{row.points}</b></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="ledger shell">
        <div className="section-heading"><div><div className="eyebrow"><span>PARSED</span> Source audit</div><h2>Opening five.</h2></div><p>Each compact record retains source identity, venue, toss, innings totals and the official outcome.</p></div>
        <div className="match-list">
          {matches.map((match, index) => (
            <article key={match.id}>
              <span className="match-no">M{String(index + 1).padStart(2, "0")}</span>
              <div><small>{match.date} · {match.city}</small><h3>{match.teams[0].abbr} <i>v</i> {match.teams[1].abbr}</h3></div>
              <p>{match.outcome.winner?.abbr ?? "NR"}<small>{match.outcome.margin ? `by ${match.outcome.margin.value} ${match.outcome.margin.unit}` : match.outcome.type}</small></p>
            </article>
          ))}
        </div>
      </section>

      <footer className="shell">
        <div className="wordmark">HOW FLUKY<span>?</span></div>
        <p>Built from Cricsheet ball-by-ball data.<br />Numbers before narratives.</p>
        <span>Pipeline milestone 01 / 08</span>
      </footer>
    </main>
  );
}
