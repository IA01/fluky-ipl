import Link from "next/link";
import { SeasonPicker } from "@/components/SeasonPicker";
import { getAnalytics } from "@/lib/data";
import { pct, teamClass } from "@/lib/format";
import { YEARS, type Team } from "@/lib/types";

type SeasonSummary = {
  season: number;
  champion: Team;
  champion_title_probability: number;
  fluke_score: number;
  robbery: { team: Team; title_probability: number };
  dominance: { team: Team; elo_gap_to_field: number };
};

type Analytics = {
  seasons: SeasonSummary[];
  flukiest_champions: SeasonSummary[];
  biggest_robberies: SeasonSummary[];
  most_dominant: SeasonSummary[];
  momentum: { team_seasons_tested: number; significant_at_5pct: number; significant_share: number };
  regression_to_mean: { pairs: number; correlation: number; persistence_slope: number };
};

export default function Home() {
  const analytics = getAnalytics<Analytics>("index");
  const flukiest = analytics.flukiest_champions[0];
  const robbery = analytics.biggest_robberies[0];
  const dominant = analytics.most_dominant[0];

  return (
    <main id="main">
      <section className="hero shell">
        <div className="eyebrow"><span>190,000</span> alternate IPL histories</div>
        <h1>Did the best<br />team actually <em>win?</em></h1>
        <div className="hero-bottom">
          <p className="dek">Every IPL season from 2008 to 2026, replayed 10,000 times. Skill gets a rating. Luck gets a number.</p>
          <SeasonPicker years={YEARS} />
        </div>
        <div className="hero-meta"><span>19 seasons</span><span>1,243 source records</span><span>Fixed-seed simulations</span></div>
      </section>

      <section className="scoreboard">
        <div className="shell score-grid">
          <div>
            <div className="eyebrow amber"><span>THE ANSWER</span> Luck leaves fingerprints</div>
            <h2>{flukiest.season}<br />was chaos.</h2>
            <p><b>{flukiest.champion.name}</b> lifted the trophy in reality, but won only {pct(flukiest.champion_title_probability)} of the model’s replays.</p>
            <Link className="text-link dark" href={`/season/${flukiest.season}/`}>Open the season <span>↗</span></Link>
          </div>
          <div className="stat-stack">
            <article><small>Champion win rate</small><strong>{pct(flukiest.champion_title_probability)}</strong><b>Flukiest champion</b></article>
            <article><small>Biggest robbery</small><strong>{robbery.robbery.team.abbr}</strong><b>{robbery.season} · {pct(robbery.robbery.title_probability)} title odds</b></article>
            <article><small>Largest Elo gap</small><strong>{dominant.dominance.elo_gap_to_field.toFixed(0)}</strong><b>{dominant.season} · {dominant.dominance.team.abbr}</b></article>
          </div>
        </div>
      </section>

      <section className="ranking-section shell" id="seasons">
        <div className="section-heading">
          <div><div className="eyebrow"><span>01</span> Champion luck</div><h2>The fluke table.</h2></div>
          <p>Lower simulated title odds mean a less repeatable championship. This is uncertainty quantified—not a claim that the trophy was undeserved.</p>
        </div>
        <div className="rank-list">
          {analytics.flukiest_champions.map((row, index) => (
            <Link href={`/season/${row.season}/`} className="rank-row" key={row.season}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <strong>{row.season}</strong>
              <div><i className={teamClass(row.champion.id)} />{row.champion.name}<small>Champion</small></div>
              <b>{pct(row.champion_title_probability)}</b>
              <em>→</em>
            </Link>
          ))}
        </div>
      </section>

      <section className="feature-band">
        <div className="shell feature-grid">
          <article>
            <div className="eyebrow"><span>LIVE</span> What-If Machine</div>
            <h2>Change one result.<br />Rewrite a season.</h2>
            <p>Flip any league match, bend team strength, and run 1,000 new seasons in your browser.</p>
            <Link className="button" href="/what-if/">Enter the machine <span>→</span></Link>
          </article>
          <div className="orbit" aria-hidden="true"><i /><i /><i /><b>1,000<br /><span>replays</span></b></div>
        </div>
      </section>

      <section className="evidence shell">
        <div className="section-heading">
          <div><div className="eyebrow"><span>02</span> Beyond the trophy</div><h2>The myths, tested.</h2></div>
          <p>The same archive tests momentum, repeatability, venue effects and player impact—not just season outcomes.</p>
        </div>
        <div className="evidence-grid">
          <article><small>Momentum</small><strong>{pct(analytics.momentum.significant_share)}</strong><p>of team-seasons show significant clustering—almost exactly the 5% expected by chance.</p></article>
          <article><small>Rating persistence</small><strong>{analytics.regression_to_mean.correlation.toFixed(2)}</strong><p>next-season correlation across {analytics.regression_to_mean.pairs} returning team pairs. Standout years fade fast.</p></article>
          <article><small>Second opinion</small><strong>295k</strong><p>deliveries feed an independent venue-and-phase-adjusted ball rating.</p></article>
        </div>
        <div className="link-rail"><Link href="/greatest/">Greatest teams →</Link><Link href="/matches/">Famous finals →</Link><Link href="/methods/">Read the methods →</Link></div>
      </section>
    </main>
  );
}
