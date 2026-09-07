"use client";

import { useMemo, useState } from "react";
import { pct, signed, teamClass } from "@/lib/format";
import type { Team } from "@/lib/types";

type Fixture = {
  id: string;
  date: string;
  team_a: string;
  team_b: string;
  probability_a: number;
  actual_winner: string | null;
  no_result: boolean;
  home_team_id: string | null;
};
type MachineSeason = {
  seed: number;
  playoff_format: string;
  teams: Array<{ team: Team; rating: number; actual_points: number; actual_position: number }>;
  fixtures: Fixture[];
};
type MachineData = {
  simulation_count: number;
  elo_scale: number;
  home_advantage: number;
  mega_auction_years: number[];
  mega_auction_carryover: number;
  normal_carryover: number;
  seasons: Record<string, MachineSeason>;
};

function mulberry32(seed: number) {
  return () => {
    let value = seed += 0x6D2B79F5;
    value = Math.imul(value ^ value >>> 15, value | 1);
    value ^= value + Math.imul(value ^ value >>> 7, value | 61);
    return ((value ^ value >>> 14) >>> 0) / 4294967296;
  };
}

function hashInputs(year: number, flipped: string, home: boolean, carry: number, adjustments: Record<string, number>) {
  const string = `${year}|${flipped}|${home}|${carry}|${Object.entries(adjustments).sort().join(";")}`;
  let hash = 2166136261;
  for (let index = 0; index < string.length; index++) hash = Math.imul(hash ^ string.charCodeAt(index), 16777619);
  return hash >>> 0;
}

function probability(left: number, right: number, scale: number, edge = 0) {
  return 1 / (1 + 10 ** (-(left + edge - right) / scale));
}

function simulate(
  data: MachineData,
  year: number,
  flipped: string,
  homeOn: boolean,
  carryover: number,
  adjustments: Record<string, number>,
) {
  const season = data.seasons[String(year)];
  const count = data.simulation_count;
  const random = mulberry32(season.seed ^ hashInputs(year, flipped, homeOn, carryover, adjustments));
  const ids = season.teams.map((row) => row.team.id);
  const index = new Map(ids.map((id, position) => [id, position]));
  const defaultCarry = data.mega_auction_years.includes(year) ? data.mega_auction_carryover : data.normal_carryover;
  const ratings = season.teams.map((row) => 1500 + (row.rating - 1500) * (carryover / defaultCarry) + row.rating * ((adjustments[row.team.id] ?? 0) / 100));
  const pointTotals = Array(ids.length).fill(0);
  const positionTotals = Array(ids.length).fill(0);
  const titles = Array(ids.length).fill(0);

  const play = (a: number, b: number) => random() < probability(ratings[a], ratings[b], data.elo_scale) ? a : b;
  for (let run = 0; run < count; run++) {
    const points = Array(ids.length).fill(0);
    const wins = Array(ids.length).fill(0);
    const margin = Array(ids.length).fill(0);
    for (const fixture of season.fixtures) {
      const a = index.get(fixture.team_a)!;
      const b = index.get(fixture.team_b)!;
      if (fixture.no_result) { points[a]++; points[b]++; continue; }
      let winner: number;
      if (fixture.id === flipped && fixture.actual_winner) {
        winner = fixture.actual_winner === fixture.team_a ? b : a;
      } else {
        const edge = homeOn ? (fixture.home_team_id === fixture.team_a ? 40 : fixture.home_team_id === fixture.team_b ? -40 : 0) : 0;
        winner = random() < probability(ratings[a], ratings[b], data.elo_scale, edge) ? a : b;
      }
      const loser = winner === a ? b : a;
      points[winner] += 2;
      wins[winner]++;
      const swing = .2 + Math.abs(ratings[a] - ratings[b]) / 500 + random();
      margin[winner] += swing;
      margin[loser] -= swing;
    }
    const order = ids.map((_, idx) => idx).sort((a, b) => points[b] - points[a] || wins[b] - wins[a] || margin[b] - margin[a] || random() - .5);
    order.forEach((teamIndex, position) => { pointTotals[teamIndex] += points[teamIndex]; positionTotals[teamIndex] += position + 1; });
    let champion: number;
    if (season.playoff_format === "two_semifinals_final") {
      champion = play(play(order[0], order[3]), play(order[1], order[2]));
    } else {
      const q1Winner = play(order[0], order[1]);
      const q1Loser = q1Winner === order[0] ? order[1] : order[0];
      const eliminator = play(order[2], order[3]);
      champion = play(q1Winner, play(q1Loser, eliminator));
    }
    titles[champion]++;
  }
  return season.teams.map((row, teamIndex) => ({
    ...row,
    expectedPoints: pointTotals[teamIndex] / count,
    expectedPosition: positionTotals[teamIndex] / count,
    titleProbability: titles[teamIndex] / count,
    adjustedRating: ratings[teamIndex],
  })).sort((a, b) => a.expectedPosition - b.expectedPosition);
}

export function WhatIfMachine({ data }: { data: MachineData }) {
  const years = Object.keys(data.seasons).map(Number);
  const [year, setYear] = useState(2019);
  const [flipped, setFlipped] = useState("");
  const [homeOn, setHomeOn] = useState(false);
  const [adjustments, setAdjustments] = useState<Record<string, number>>({});
  const defaultCarry = data.mega_auction_years.includes(year) ? data.mega_auction_carryover : data.normal_carryover;
  const [carryByYear, setCarryByYear] = useState<Record<number, number>>({});
  const carry = carryByYear[year] ?? defaultCarry;
  const season = data.seasons[String(year)];
  const teams = new Map(season.teams.map((row) => [row.team.id, row.team]));
  const eligibleFixtures = season.fixtures.filter((fixture) => !fixture.no_result && fixture.actual_winner);
  const results = useMemo(() => simulate(data, year, flipped, homeOn, carry, adjustments), [data, year, flipped, homeOn, carry, adjustments]);
  const maxTitle = Math.max(...results.map((row) => row.titleProbability));

  const changeYear = (nextYear: number) => { setYear(nextYear); setFlipped(""); setAdjustments({}); };
  return (
    <div className="machine">
      <div className="machine-controls">
        <label><span>Season</span><select value={year} onChange={(event) => changeYear(Number(event.target.value))}>{years.map((value) => <option key={value}>{value}</option>)}</select></label>
        <label><span>Force one upset</span><select value={flipped} onChange={(event) => setFlipped(event.target.value)}><option value="">No forced result</option>{eligibleFixtures.map((fixture, matchIndex) => {
          const winner = teams.get(fixture.actual_winner!)!;
          const loserId = fixture.actual_winner === fixture.team_a ? fixture.team_b : fixture.team_a;
          return <option value={fixture.id} key={fixture.id}>M{matchIndex + 1}: {winner.abbr} loss to {teams.get(loserId)!.abbr}</option>;
        })}</select></label>
        <label className="toggle-control"><span>Home edge</span><button type="button" role="switch" aria-checked={homeOn} onClick={() => setHomeOn((value) => !value)}><i />{homeOn ? "+40 Elo" : "Fitted 0"}</button></label>
      </div>

      <div className="carry-control">
        <div><span>{data.mega_auction_years.includes(year) ? "Mega-auction" : "Normal-year"} carryover</span><b>{Math.round(carry * 100)}%</b></div>
        <input aria-label="Rating carryover" type="range" min="5" max="100" value={Math.round(carry * 100)} onChange={(event) => setCarryByYear((current) => ({ ...current, [year]: Number(event.target.value) / 100 }))} />
        <small>Model default: {Math.round(defaultCarry * 100)}%. Mega-auction years are 2011, 2014, 2018, 2022 and 2025.</small>
      </div>

      <div className="machine-output">
        <section>
          <div className="machine-heading"><div><small>Counterfactual table</small><h2>{year}, replayed.</h2></div><b>{data.simulation_count.toLocaleString()} runs</b></div>
          <div className="table-wrap"><table className="machine-table"><thead><tr><th>Exp.</th><th>Team</th><th>Pts</th><th>Actual</th><th>Delta</th><th>Title</th></tr></thead><tbody>{results.map((row, position) => <tr key={row.team.id}><td>{position + 1}</td><td><i className={teamClass(row.team.id)} />{row.team.name}<small>{row.team.abbr}</small></td><td><b>{row.expectedPoints.toFixed(1)}</b></td><td>{row.actual_points}</td><td>{signed(row.expectedPoints - row.actual_points)}</td><td>{pct(row.titleProbability)}</td></tr>)}</tbody></table></div>
        </section>
        <aside>
          <small>Live title odds</small>
          <div className="live-odds">{[...results].sort((a, b) => b.titleProbability - a.titleProbability).map((row) => <div key={row.team.id}><header><b><i className={teamClass(row.team.id)} />{row.team.abbr}</b><span>{pct(row.titleProbability)}</span></header><div><i className={teamClass(row.team.id)} style={{ width: `${row.titleProbability / maxTitle * 100}%` }} /></div></div>)}</div>
        </aside>
      </div>

      <details className="strength-panel"><summary>Adjust individual team strength <span>±10%</span></summary><div>{season.teams.map((row) => <label key={row.team.id}><span><i className={teamClass(row.team.id)} />{row.team.abbr}</span><input aria-label={`${row.team.name} strength adjustment`} type="range" min="-10" max="10" value={adjustments[row.team.id] ?? 0} onChange={(event) => setAdjustments((current) => ({ ...current, [row.team.id]: Number(event.target.value) }))} /><b>{signed(adjustments[row.team.id] ?? 0, 0)}%</b></label>)}</div></details>
      <p className="model-note">Same match-level structure as the 10,000-run pipeline; this client version uses {data.simulation_count.toLocaleString()} fixed-seed replays for speed. A forced upset locks only the chosen result and simulates every other league fixture.</p>
    </div>
  );
}
