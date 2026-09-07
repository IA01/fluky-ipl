"use client";

import { useMemo, useState } from "react";
import { pct, teamClass } from "@/lib/format";
import type { Team } from "@/lib/types";

type State = {
  ball: string;
  innings: number;
  batting_team_id: string;
  score: number;
  wickets: number;
  runs_required: number | null;
  balls_remaining: number | null;
  team_a_win_probability: number;
};
type FamousMatch = {
  season: number;
  match_id: string;
  title: string;
  date: string;
  venue: string;
  team_a: Team;
  team_b: Team;
  winner: Team;
  pre_match_probability_team_a: number;
  turning_point_index: number;
  states: State[];
};

export function MatchExplorer({ matches }: { matches: FamousMatch[] }) {
  const [selected, setSelected] = useState(matches.findIndex((match) => match.season === 2019));
  const match = matches[Math.max(0, selected)];
  const [ballByMatch, setBallByMatch] = useState<Record<string, number>>({});
  const cursor = Math.min(ballByMatch[match.match_id] ?? match.states.length - 1, match.states.length - 1);
  const state = match.states[cursor];
  const points = useMemo(() => match.states.map((row, index) => {
    const x = match.states.length === 1 ? 0 : index / (match.states.length - 1) * 1000;
    const y = 300 - row.team_a_win_probability * 280;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" "), [match]);
  const cursorX = match.states.length === 1 ? 0 : cursor / (match.states.length - 1) * 1000;

  return (
    <div className="match-explorer">
      <div className="match-controls">
        <label><span>Choose a final</span><select value={selected} onChange={(event) => setSelected(Number(event.target.value))}>{matches.map((row, index) => <option value={index} key={row.match_id}>{row.season} · {row.team_a.abbr} v {row.team_b.abbr}</option>)}</select></label>
        <div><small>{match.date}</small><span>{match.venue}</span></div>
      </div>
      <div className="match-scoreline">
        <div><i className={teamClass(match.team_a.id)} /><strong>{match.team_a.abbr}</strong><span>{pct(state.team_a_win_probability)}</span></div>
        <em>win probability</em>
        <div><span>{pct(1 - state.team_a_win_probability)}</span><strong>{match.team_b.abbr}</strong><i className={teamClass(match.team_b.id)} /></div>
      </div>
      <div className="wp-chart-wrap">
        <svg className="wp-chart" viewBox="0 0 1000 320" preserveAspectRatio="none" role="img" aria-label={`${match.title} win probability by ball`}>
          {[0, .25, .5, .75, 1].map((value) => <line key={value} x1="0" x2="1000" y1={300 - value * 280} y2={300 - value * 280} />)}
          <polygon points={`0,300 ${points} 1000,300`} />
          <polyline className={teamClass(match.team_a.id)} points={points} />
          <line className="cursor" x1={cursorX} x2={cursorX} y1="20" y2="300" />
          <circle className={teamClass(match.team_a.id)} cx={cursorX} cy={300 - state.team_a_win_probability * 280} r="8" />
        </svg>
        <span className="wp-label top">100%</span><span className="wp-label middle">50%</span><span className="wp-label bottom">0%</span>
      </div>
      <input className="scrubber" aria-label="Scrub through the match" type="range" min="0" max={match.states.length - 1} value={cursor} onChange={(event) => setBallByMatch((current) => ({ ...current, [match.match_id]: Number(event.target.value) }))} />
      <div className="state-card">
        <div><small>Ball</small><strong>{state.ball}</strong></div>
        <div><small>Innings</small><strong>{state.innings}</strong></div>
        <div><small>Score</small><strong>{state.score}/{state.wickets}</strong></div>
        <div><small>{state.runs_required === null ? "Pre-match prior" : "Equation"}</small><strong>{state.runs_required === null ? pct(match.pre_match_probability_team_a) : `${state.runs_required} off ${state.balls_remaining}`}</strong></div>
      </div>
      <p className="model-note">Descriptive resource-state estimate. The largest one-ball probability swing occurred at ball {match.states[match.turning_point_index]?.ball ?? "—"}.</p>
    </div>
  );
}
