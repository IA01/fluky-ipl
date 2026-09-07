import type { Metadata } from "next";
import Link from "next/link";
import { getAnalytics, getRating, getSeason } from "@/lib/data";
import { pct } from "@/lib/format";
import { YEARS } from "@/lib/types";

export const metadata: Metadata = { title: "Methods" };

type Calibration = {
  selection_metric: string;
  holdout_seasons: number[];
  selected: { elo_scale: number; home_advantage: number; k_factor: number };
  coin_flip_log_loss: number;
  grid: Array<{ log_loss: number; brier_score: number; matches: number }>;
};
type Robustness = {
  method: { venue_shrinkage: string; team_value: string };
  comparison_to_elo: { overall_correlation: number; team_seasons: number };
};
type Analytics = {
  momentum: { test: string; team_seasons_tested: number; significant_at_5pct: number; significant_share: number };
  regression_to_mean: { pairs: number; correlation: number; persistence_slope: number };
  toss_dew_proxy: Array<{ venue: string; matches: number; chase_win_rate: number; field_toss_win_rate: number | null }>;
};

export default function MethodsPage() {
  const calibration = getRating<Calibration>("calibration");
  const robustness = getRating<Robustness>("robustness");
  const analytics = getAnalytics<Analytics>("index");
  const seasons = YEARS.map((year) => getSeason(year).parsed);
  const records = seasons.reduce((sum, season) => sum + season.summary.records, 0);
  const official = seasons.reduce((sum, season) => sum + season.summary.matches, 0);
  const league = seasons.reduce((sum, season) => sum + season.summary.league_matches, 0);
  const exceptions = seasons.flatMap((season) => season.matches
    .filter((match) => match.source_kind !== "cricsheet_ball_by_ball" || match.counts_for_table === false)
    .map((match) => ({ year: season.season, ...match }) as {
      year: number; id: unknown; teams?: unknown; source_note?: unknown; reason?: unknown;
    }));
  const topVenues = analytics.toss_dew_proxy.slice(0, 8);

  return (
    <main id="main">
      <section className="page-hero shell">
        <div className="eyebrow"><span>OPEN BOOK</span> data, assumptions, limitations</div>
        <h1>Trust the work.<br /><em>Inspect the work.</em></h1>
        <p>The claim is only as strong as the audit trail. Here is the complete route from 295,732 deliveries to 190,000 alternate seasons.</p>
        <div className="hero-meta"><span>fixed seeds</span><span>published-table checks</span><span>two strength models</span></div>
      </section>

      <section className="methods-body shell">
        <aside className="methods-index"><small>On this page</small><a href="#data">01 / Data</a><a href="#elo">02 / Elo</a><a href="#sim">03 / Simulation</a><a href="#robust">04 / Robustness</a><a href="#tests">05 / Other tests</a><a href="#limits">06 / Limits</a></aside>
        <div className="methods-copy">
          <section id="data">
            <div className="eyebrow"><span>01</span> Data integrity</div><h2>Rebuild the record first.</h2>
            <p>Cricsheet’s IPL JSON is the ball-level source. The parser normalises dates, teams, tosses, venues, innings, super-over outcomes and match stages into a stable season schema. It contains {records.toLocaleString()} source and supplemental records representing {official.toLocaleString()} official matches, of which {league.toLocaleString()} are league fixtures.</p>
            <p>Delhi Daredevils/Capitals, Kings XI/Punjab Kings and Bangalore/Bengaluru are continuous identities. Deccan Chargers and Sunrisers Hyderabad remain separate because SRH was a replacement franchise. Rising Pune Supergiant and Gujarat Lions remain independent of the suspended CSK and RR.</p>
            <h3>The missing-match audit</h3>
            <p>Ball-by-ball archives naturally omit games where no ball was bowled. We compare each season’s parsed records with the published final table, then explicitly add or exclude only documented exceptions.</p>
            <div className="exception-list">{exceptions.map((match) => <article key={`${match.year}-${String(match.id)}`}><b>{match.year}</b><span>{Array.isArray(match.teams) ? (match.teams as Array<{ abbr?: string; name?: string }>).map((team) => team.abbr ?? team.name).join(" v ") : String(match.id)}</span><p>{String(match.source_note ?? match.reason ?? "Documented no-result/table exception")}</p></article>)}</div>
            <p className="callout"><b>Hard validation:</b> every season must reconcile every team’s played, won, lost, no-result and points fields to an independently published final table. A mismatch stops the pipeline. Published ordering and NRR remain authoritative; calculated NRR is retained for audit.</p>
          </section>

          <section id="elo">
            <div className="eyebrow"><span>02</span> Team strength</div><h2>One result model. No drift.</h2>
            <p>Each team starts around 1500 Elo. New franchises begin at 1465. After each eligible match, the winner gains and loser sheds <code>K × margin multiplier × (actual − expected)</code>, with K={calibration.selected.k_factor}. Win probability is <code>1 / (1 + 10^(−rating difference / {calibration.selected.elo_scale}))</code>.</p>
            <h3>Margin of victory</h3>
            <p>Run wins use <code>1 + min(1.25, ln(1 + runs) / ln(51))</code>. Wicket wins use <code>1 + min(1.25, 0.65 × wickets/10 + 0.60 × balls remaining/quota)</code>. No-results and abandoned games never update Elo.</p>
            <h3>Auction-cycle carryover</h3>
            <p>This is explicitly auction-aware. Mega-auction years <b>2011, 2014, 2018, 2022 and 2025</b> retain 10% of the prior rating edge; normal years retain 40%. The reset is <code>1500 + carryover × (prior rating − prior-season field mean)</code>.</p>
            <h3>Home and calibration</h3>
            <p>A venue-to-home map applies an edge only when that franchise is playing and the stage is not neutral. South Africa 2009 and neutral 2020–22 configurations receive no home term. A grid search across K, Elo scale and home edge selected scale {calibration.selected.elo_scale}, K {calibration.selected.k_factor} and a fitted home edge of {calibration.selected.home_advantage}. Zero is a result, not an omission.</p>
            <div className="metric-pair"><article><small>Holdout log loss</small><strong>{calibration.grid[0].log_loss.toFixed(4)}</strong><span>{calibration.grid[0].matches} matches · {calibration.holdout_seasons[0]}–{calibration.holdout_seasons[1]}</span></article><article><small>50/50 baseline</small><strong>{calibration.coin_flip_log_loss.toFixed(4)}</strong><span>The chosen model must beat this or the build fails.</span></article></div>
            <p className="callout"><b>Interpretation guardrail:</b> calibration uses league-end Elo retrospectively against that season’s results. This measures season strength for counterfactual replay; it is not a pre-match forecasting claim.</p>
          </section>

          <section id="sim">
            <div className="eyebrow"><span>03</span> Monte Carlo</div><h2>Replay matches, not balls.</h2>
            <p>Each season replays its actual league fixture list 10,000 times with a fixed season seed. A Bernoulli draw uses the two teams’ league-end ratings. Observed no-results remain one point each. Points, wins and a sampled symmetric performance-margin proxy rank the table.</p>
            <p>The top four enter the season’s real bracket: two semifinals plus final through 2010, then the Page system (Qualifier 1, Eliminator, Qualifier 2, Final). Every output includes points and position distributions, playoff/final/title probabilities, expected points and expected position.</p>
            <p>“Luck index” is actual points minus simulated median points. “Title luck” is one minus the actual champion’s title probability. A high number means a rarer outcome—not an illegitimate one.</p>
          </section>

          <section id="robust">
            <div className="eyebrow"><span>04</span> Independent robustness</div><h2>Ask the balls themselves.</h2>
            <p>The second strength rating does not use match wins. Batting value is runs above season/venue/phase par; bowling is equivalent runs saved. Phases are powerplay (overs 1–6), middle (7–15), and death (16–20). {robustness.method.venue_shrinkage}</p>
            <p>Its season-standardized rating correlates {robustness.comparison_to_elo.overall_correlation.toFixed(2)} with Elo across {robustness.comparison_to_elo.team_seasons} team-seasons. Agreement is reassuring; disagreement remains visible rather than being tuned away.</p>
            <p>Player impact applies the same above-par framework and adds 15 runs per bowler-credited wicket. It is an interpretable portfolio metric, not a claim to isolate every fielding or matchup effect.</p>
          </section>

          <section id="tests">
            <div className="eyebrow"><span>05</span> Beyond simulation</div><h2>Put the folklore on trial.</h2>
            <p><b>Momentum:</b> a Wald–Wolfowitz runs test asks whether wins and losses cluster. {analytics.momentum.significant_at_5pct} of {analytics.momentum.team_seasons_tested} team-seasons are significant at 5% ({pct(analytics.momentum.significant_share)}), essentially the false-positive share expected under the null.</p>
            <p><b>Regression to the mean:</b> league-end Elo has a {analytics.regression_to_mean.correlation.toFixed(3)} next-season correlation across {analytics.regression_to_mean.pairs} returning team pairs, with a {analytics.regression_to_mean.persistence_slope.toFixed(3)} persistence slope.</p>
            <p><b>Toss/dew proxy:</b> chase win rate and win rate after choosing to field are reported per venue. They are descriptive, not causal: toss choice, team strength, weather and dew are confounded.</p>
            <div className="venue-table">{topVenues.map((row) => <article key={row.venue}><span>{row.venue}</span><b>{row.matches}</b><em>{pct(row.chase_win_rate)}</em><i>{row.field_toss_win_rate === null ? "—" : pct(row.field_toss_win_rate)}</i></article>)}</div>
            <div className="venue-head"><span>Venue</span><b>Matches</b><em>Chase W%</em><i>Field-toss W%</i></div>
          </section>

          <section id="limits">
            <div className="eyebrow"><span>06</span> Limitations</div><h2>Precision without pretending.</h2>
            <ul><li>Retrospective league-end strength intentionally knows how good a team proved to be that season; do not read probabilities as contemporaneous betting odds.</li><li>Match-level replay cannot calculate true counterfactual NRR, so a calibrated-looking but deliberately non-fabricated margin proxy breaks equal-points ties.</li><li>Observed no-results are preserved, not re-sampled from weather forecasts.</li><li>The in-match win-probability graph is a descriptive resource-state model, not archived market odds.</li><li>Above-par player impact does not fully isolate fielding, opposition, roles or replacement value.</li></ul>
            <h3>Sources</h3>
            <p><a href="https://cricsheet.org/downloads/" target="_blank" rel="noreferrer">Cricsheet IPL JSON ↗</a> · <a href="https://www.iplt20.com/" target="_blank" rel="noreferrer">Official IPL reports ↗</a> · published season tables are linked from every season page. The pipeline, configs and exact exceptions live in the <a href="https://github.com/IA01/fluky-ipl" target="_blank" rel="noreferrer">public repository ↗</a>.</p>
            <Link className="button" href="/what-if/">Stress-test the model <span>→</span></Link>
          </section>
        </div>
      </section>
    </main>
  );
}
