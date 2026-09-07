import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ProbabilityBar } from "@/components/ProbabilityBar";
import { SeasonPicker } from "@/components/SeasonPicker";
import { getRating, getSeason } from "@/lib/data";
import { pct, signed, teamClass } from "@/lib/format";
import { YEARS, type Team } from "@/lib/types";

type Robustness = {
  seasons: Record<string, Array<{
    team: Team;
    matches: number;
    batting_runs_above_par: number;
    bowling_runs_saved: number;
    runs_above_par_per_match: number;
    rating_z: number;
  }>>;
};

export function generateStaticParams() {
  return YEARS.map((year) => ({ year: String(year) }));
}

export function generateMetadata({ params }: { params: { year: string } }): Metadata {
  return { title: `${params.year} season` };
}

export default function SeasonPage({ params }: { params: { year: string } }) {
  const year = Number(params.year);
  if (!YEARS.includes(year)) notFound();
  const { parsed, simulation } = getSeason(year);
  const robustness = getRating<Robustness>("robustness").seasons[String(year)];
  const titleRows = [...simulation.teams].sort((a, b) => b.title_probability - a.title_probability);
  const maxTitle = Math.max(...titleRows.map((row) => row.title_probability));
  const maxPointsCount = Math.max(
    ...simulation.teams.flatMap((row) => Object.values(row.points_distribution)),
  );
  const champion = simulation.teams.find((row) => row.team.id === simulation.actual_champion.id)!;
  const prev = YEARS.includes(year - 1) ? year - 1 : null;
  const next = YEARS.includes(year + 1) ? year + 1 : null;

  return (
    <main id="main">
      <section className="season-hero shell">
        <div className="season-kicker"><span>IPL / {year}</span><SeasonPicker current={year} years={YEARS} /></div>
        <h1>{year}</h1>
        <div className="season-verdict">
          <div><small>Actual champion</small><strong><i className={teamClass(simulation.actual_champion.id)} />{simulation.actual_champion.name}</strong></div>
          <div><small>Won the replay</small><strong>{pct(simulation.champion_title_probability)}</strong></div>
          <div><small>Luck score</small><strong>{pct(simulation.fluke_score)}</strong></div>
        </div>
        <p>The champion appeared in roughly one of every {Math.max(1, Math.round(1 / simulation.champion_title_probability))} simulated title outcomes. Their actual {champion.actual_points} points were {signed(champion.actual_points - champion.expected_points)} versus the model expectation.</p>
        <small className="metric-footnote">Hero comparison uses simulated mean points; the table’s Luck column uses the simulated median.</small>
      </section>

      <section className="season-data shell">
        <div className="section-heading compact">
          <div><div className="eyebrow"><span>01</span> Expected v actual</div><h2>Where luck moved the table.</h2></div>
          <p>Luck index is actual points minus the simulated median. Positive is above expectation; negative is below.</p>
        </div>
        <div className="table-wrap">
          <table className="comparison-table">
            <thead><tr><th>Actual</th><th>Team</th><th>Pts</th><th>Expected</th><th>Median</th><th>Luck</th><th>Expected pos.</th></tr></thead>
            <tbody>{simulation.teams.map((row) => (
              <tr key={row.team.id}>
                <td>{String(row.actual_position).padStart(2, "0")}</td>
                <td><i className={teamClass(row.team.id)} />{row.team.name}<small>{row.team.abbr}</small></td>
                <td><b>{row.actual_points}</b></td>
                <td>{row.expected_points.toFixed(1)}</td>
                <td>{row.median_points.toFixed(0)}</td>
                <td className={row.luck_index > 0 ? "positive" : row.luck_index < 0 ? "negative" : ""}>{signed(row.luck_index)}</td>
                <td>{row.expected_position.toFixed(1)}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </section>

      <section className="paper-panel">
        <div className="shell split-section">
          <div>
            <div className="eyebrow amber"><span>02</span> Title odds</div>
            <h2>The trophy field.</h2>
            <p>{simulation.robbery.team.name} posted the highest non-winner chance at {pct(simulation.robbery.title_probability)}.</p>
          </div>
          <div className="prob-list dark-bars">
            {titleRows.map((row) => <ProbabilityBar team={row.team} value={row.title_probability} max={maxTitle} key={row.team.id} />)}
          </div>
        </div>
      </section>

      <section className="distribution-section shell">
        <div className="section-heading compact">
          <div><div className="eyebrow"><span>03</span> 10,000 seasons</div><h2>Points, distributed.</h2></div>
          <p>Every bar is a count of simulations at that points total. The lime marker is the team’s actual haul.</p>
        </div>
        <div className="histogram-grid">
          {simulation.teams.map((row) => {
            const entries = Object.entries(row.points_distribution).sort((a, b) => Number(a[0]) - Number(b[0]));
            return <article key={row.team.id}>
              <header><b><i className={teamClass(row.team.id)} />{row.team.abbr}</b><span>{row.expected_points.toFixed(1)} expected</span></header>
              <div className="histogram" aria-label={`${row.team.name} simulated points distribution`}>
                {entries.map(([points, count]) => <i
                  className={Number(points) === row.actual_points ? "actual" : ""}
                  key={points}
                  title={`${points} points: ${count} simulations`}
                  style={{ height: `${Math.max(3, count / maxPointsCount * 100)}%` }}
                />)}
              </div>
              <small>{Math.min(...entries.map(([p]) => Number(p)))} pts <span>actual {row.actual_points}</span> {Math.max(...entries.map(([p]) => Number(p)))} pts</small>
            </article>;
          })}
        </div>
      </section>

      <section className="audit-band">
        <div className="shell audit-grid">
          <div><div className="eyebrow"><span>VALIDATED</span> Published table check</div><h2>{parsed.validation.status}.</h2><p>All {parsed.validation.teams_checked} teams’ played, won, lost, no-result and points fields reconcile to the published final table.</p><a href={parsed.validation.source_url} target="_blank" rel="noreferrer" className="text-link">View reference table ↗</a></div>
          <div className="audit-cards">
            <article><small>Official matches</small><b>{parsed.summary.matches}</b></article>
            <article><small>League / playoffs</small><b>{parsed.summary.league_matches} / {parsed.summary.playoff_matches}</b></article>
            <article><small>Independent ball leader</small><b>{robustness[0].team.abbr}</b><span>{signed(robustness[0].runs_above_par_per_match)} runs/match</span></article>
            <article><small>Playoff format</small><b>{parsed.config.playoff_format === "page_playoff" ? "Page" : "Semis"}</b></article>
          </div>
        </div>
      </section>

      <nav className="season-nav shell" aria-label="Adjacent seasons">
        {prev ? <Link href={`/season/${prev}/`}>← {prev}</Link> : <span />}
        <Link href="/what-if/">Rewrite this season</Link>
        {next ? <Link href={`/season/${next}/`}>{next} →</Link> : <span />}
      </nav>
    </main>
  );
}
