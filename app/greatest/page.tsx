import type { Metadata } from "next";
import { getAnalytics, getRating, getSeason } from "@/lib/data";
import { signed, teamClass } from "@/lib/format";
import { YEARS, type Team } from "@/lib/types";

export const metadata: Metadata = { title: "Greatest IPL teams" };

type EloData = {
  model: Record<string, unknown>;
  seasons: Record<string, { league_end: Record<string, number> }>;
};
type Robustness = { comparison_to_elo: { overall_correlation: number; team_seasons: number } };
type PlayerPeak = {
  season: number;
  player: string;
  matches: number;
  batting_runs_above_par: number;
  bowling_impact_runs: number;
  bowler_wickets: number;
};
type Players = { leaderboards: { batting: PlayerPeak[]; bowling: PlayerPeak[] } };

export default function GreatestPage() {
  const elo = getRating<EloData>("elo");
  const robustness = getRating<Robustness>("robustness");
  const players = getAnalytics<Players>("players");
  const teams = new Map<string, Team>();
  YEARS.forEach((year) => getSeason(year).simulation.teams.forEach((row) => teams.set(row.team.id, row.team)));
  const rows = YEARS.flatMap((year) => Object.entries(elo.seasons[String(year)].league_end).map(([teamId, rating]) => ({
    year,
    rating,
    team: teams.get(teamId)!,
  }))).sort((a, b) => b.rating - a.rating);
  const top = rows.slice(0, 20);
  const leaders = Array.from(teams.values()).map((team) => {
    const entries = rows.filter((row) => row.team.id === team.id).sort((a, b) => a.year - b.year);
    return { team, entries, peak: Math.max(...entries.map((row) => row.rating)) };
  }).sort((a, b) => b.peak - a.peak).slice(0, 8);
  const minRating = 1350;
  const maxRating = 1700;
  const linePath = (entries: Array<{ year: number; rating: number }>) => entries.map((entry, index) => {
    const x = (entry.year - 2008) / 18 * 1000;
    const y = 240 - (entry.rating - minRating) / (maxRating - minRating) * 220;
    return `${index ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");

  return (
    <main id="main">
      <section className="page-hero shell">
        <div className="eyebrow"><span>2008—2026</span> cross-season Elo</div>
        <h1>Greatness,<br /><em>on one scale.</em></h1>
        <p>Every team-season is measured against the same 1500-point reference. The high-water mark belongs to <b>{top[0].team.name}, {top[0].year}</b>.</p>
        <div className="hero-meta"><span>{rows.length} team-seasons</span><span>match-by-match updates</span><span>auction-aware resets</span></div>
      </section>

      <section className="paper-panel">
        <div className="shell line-chart-section">
          <div className="section-heading compact">
            <div><div className="eyebrow amber"><span>01</span> The long view</div><h2>Franchise trajectories.</h2></div>
            <p>League-end strength for the eight highest-peaking franchises. Gaps indicate seasons the franchise did not play.</p>
          </div>
          <div className="elo-chart-wrap">
            <svg className="elo-chart" viewBox="0 0 1000 260" role="img" aria-label="IPL franchise Elo by season">
              {[1400, 1500, 1600, 1700].map((rating) => {
                const y = 240 - (rating - minRating) / (maxRating - minRating) * 220;
                return <g key={rating}><line x1="0" x2="1000" y1={y} y2={y} /><text x="4" y={y - 6}>{rating}</text></g>;
              })}
              {leaders.map(({ team, entries }) => <path className={teamClass(team.id)} d={linePath(entries)} key={team.id} />)}
            </svg>
            <div className="chart-years"><span>2008</span><span>2014</span><span>2020</span><span>2026</span></div>
          </div>
          <div className="chart-legend">{leaders.map(({ team }) => <span key={team.id}><i className={teamClass(team.id)} />{team.abbr}</span>)}</div>
        </div>
      </section>

      <section className="ranking-section shell">
        <div className="section-heading compact">
          <div><div className="eyebrow"><span>02</span> Peak power</div><h2>The top 20.</h2></div>
          <p>Elo after the league stage—before a short playoff run can distort the season-strength signal.</p>
        </div>
        <div className="rank-list top-list">
          {top.map((row, index) => <div className="rank-row" key={`${row.year}-${row.team.id}`}>
            <span>{String(index + 1).padStart(2, "0")}</span><strong>{row.year}</strong>
            <div><i className={teamClass(row.team.id)} />{row.team.name}<small>{row.team.abbr}</small></div>
            <b>{row.rating.toFixed(0)}</b><em>{signed(row.rating - 1500, 0)}</em>
          </div>)}
        </div>
      </section>

      <section className="feature-band pale">
        <div className="shell split-section">
          <div><div className="eyebrow amber"><span>CHECK</span> Independent evidence</div><h2>Different lens.<br />Same signal.</h2><p>The ball-by-ball rating and Elo have a {robustness.comparison_to_elo.overall_correlation.toFixed(2)} correlation across {robustness.comparison_to_elo.team_seasons} team-seasons. It is meaningful agreement from a model that never sees match results directly.</p></div>
          <div className="correlation-mark"><strong>{robustness.comparison_to_elo.overall_correlation.toFixed(2)}</strong><span>rating correlation</span><i style={{ width: `${robustness.comparison_to_elo.overall_correlation * 100}%` }} /></div>
        </div>
      </section>

      <section className="ranking-section shell">
        <div className="section-heading compact">
          <div><div className="eyebrow"><span>03</span> Ball-level ratings</div><h2>Two disciplines.<br />Two scales.</h2></div>
          <p>Players are ranked separately because wickets heavily influence the combined measure. Batting shows runs scored above the venue-and-phase baseline. Bowling shows a composite score: estimated runs saved against that baseline, plus 15 points per credited wicket. The bowling figure is a rating, not literal runs.</p>
        </div>
        <div className="player-leaderboards">
          <section><h3>Batting above par</h3><div className="player-grid">{players.leaderboards.batting.map((row, index) => <article key={`${row.season}-${row.player}`}><span>{String(index + 1).padStart(2, "0")}</span><small>{row.season}</small><h3>{row.player}</h3><strong>{row.batting_runs_above_par.toFixed(0)}</strong><p>runs above par</p></article>)}</div></section>
          <section><h3>Bowling score</h3><div className="player-grid">{players.leaderboards.bowling.map((row, index) => <article key={`${row.season}-${row.player}`}><span>{String(index + 1).padStart(2, "0")}</span><small>{row.season}</small><h3>{row.player}</h3><strong>{row.bowling_impact_runs.toFixed(0)}</strong><p>{row.bowler_wickets} wickets · composite rating</p></article>)}</div></section>
        </div>
      </section>
    </main>
  );
}
