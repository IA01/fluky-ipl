#!/usr/bin/env python3
"""Build venue/phase robustness ratings, player impact and famous-match WP traces."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from parse_cricsheet import TeamRegistry, overs_to_balls, season_year, stage_for

ROOT = Path(__file__).resolve().parents[1]
PHASES = ("powerplay", "middle", "death")
BOWLER_WICKET_EXCLUSIONS = {"run out", "retired hurt", "retired out", "obstructing the field"}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def stable_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def phase_for(over: int) -> str:
    if over < 6:
        return "powerplay"
    if over < 15:
        return "middle"
    return "death"


def canonical_by_id(registry: TeamRegistry) -> dict[str, dict[str, str]]:
    output: dict[str, dict[str, str]] = {}
    for alias in registry.aliases:
        team = registry.resolve(alias)
        output[team["id"]] = team
    return output


def collect_events(raw_root: Path, registry: TeamRegistry) -> tuple[list[dict[str, Any]], dict[str, Path]]:
    events: list[dict[str, Any]] = []
    path_by_id: dict[str, Path] = {}
    for path in sorted(raw_root.rglob("*.json")):
        raw = load_json(path)
        info = raw.get("info", {})
        try:
            year = season_year(info.get("season"))
        except ValueError:
            continue
        path_by_id[path.stem] = path
        teams = [registry.resolve(name)["id"] for name in info["teams"]]
        venue = info.get("venue") or "Unknown venue"
        stage = stage_for(info)
        for innings_number, innings in enumerate(raw.get("innings", []), start=1):
            batting_team = registry.resolve(innings["team"])["id"]
            bowling_team = next((team_id for team_id in teams if team_id != batting_team), None)
            if not bowling_team:
                continue
            for over in innings.get("overs", []):
                phase = phase_for(int(over["over"]))
                for delivery in over.get("deliveries", []):
                    extras = delivery.get("extras", {})
                    runs = delivery.get("runs", {})
                    legal = "wides" not in extras and "noballs" not in extras
                    bowler_conceded = int(runs.get("batter", 0)) + int(extras.get("wides", 0)) + int(extras.get("noballs", 0))
                    bowler_wickets = sum(
                        wicket.get("kind") not in BOWLER_WICKET_EXCLUSIONS
                        for wicket in delivery.get("wickets", [])
                    )
                    team_wickets = sum(
                        wicket.get("kind") != "retired hurt" for wicket in delivery.get("wickets", [])
                    )
                    events.append(
                        {
                            "year": year,
                            "match_id": path.stem,
                            "stage": stage,
                            "venue": venue,
                            "innings": innings_number,
                            "over": int(over["over"]),
                            "ball": delivery.get("actual_delivery"),
                            "phase": phase,
                            "batting_team": batting_team,
                            "bowling_team": bowling_team,
                            "batter": delivery["batter"],
                            "bowler": delivery["bowler"],
                            "team_runs": int(runs.get("total", 0)),
                            "batter_runs": int(runs.get("batter", 0)),
                            "bowler_conceded": bowler_conceded,
                            "bowler_wickets": int(bowler_wickets),
                            "team_wickets": int(team_wickets),
                            "legal": int(legal),
                        }
                    )
    return events, path_by_id


def build_baselines(events: list[dict[str, Any]]) -> tuple[dict[tuple[int, str], float], dict[tuple[int, str, str], float]]:
    global_sums: dict[tuple[int, str], list[float]] = defaultdict(lambda: [0.0, 0.0])
    venue_sums: dict[tuple[int, str, str], list[float]] = defaultdict(lambda: [0.0, 0.0])
    for event in events:
        if event["stage"] != "league":
            continue
        global_key = (event["year"], event["phase"])
        venue_key = (event["year"], event["venue"], event["phase"])
        for target, key in ((global_sums, global_key), (venue_sums, venue_key)):
            target[key][0] += event["team_runs"]
            target[key][1] += event["legal"]
    global_rates = {key: runs / balls for key, (runs, balls) in global_sums.items() if balls}
    venue_rates = {}
    prior_balls = 120.0
    for key, (runs, balls) in venue_sums.items():
        global_rate = global_rates[(key[0], key[2])]
        venue_rates[key] = (runs + prior_balls * global_rate) / (balls + prior_balls)
    return global_rates, venue_rates


def build_robustness(
    events: list[dict[str, Any]],
    global_rates: dict[tuple[int, str], float],
    venue_rates: dict[tuple[int, str, str], float],
    teams: dict[str, dict[str, str]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    team_stats: dict[tuple[int, str], dict[str, Any]] = defaultdict(
        lambda: {
            "batting_runs_above_par": 0.0,
            "bowling_runs_saved": 0.0,
            "phases": defaultdict(lambda: {"batting_runs_above_par": 0.0, "bowling_runs_saved": 0.0}),
            "matches": set(),
        }
    )
    player_stats: dict[tuple[int, str], dict[str, Any]] = defaultdict(
        lambda: {"batting_runs_above_par": 0.0, "bowling_runs_saved": 0.0, "wickets": 0, "matches": set()}
    )
    for event in events:
        rate = venue_rates.get(
            (event["year"], event["venue"], event["phase"]),
            global_rates[(event["year"], event["phase"])],
        )
        expected = rate * event["legal"]
        batting_value = event["team_runs"] - expected
        bowling_value = expected - event["team_runs"]
        batting = team_stats[(event["year"], event["batting_team"])]
        bowling = team_stats[(event["year"], event["bowling_team"])]
        batting["batting_runs_above_par"] += batting_value
        batting["phases"][event["phase"]]["batting_runs_above_par"] += batting_value
        batting["matches"].add(event["match_id"])
        bowling["bowling_runs_saved"] += bowling_value
        bowling["phases"][event["phase"]]["bowling_runs_saved"] += bowling_value
        bowling["matches"].add(event["match_id"])

        batter = player_stats[(event["year"], event["batter"])]
        batter["batting_runs_above_par"] += event["batter_runs"] - expected
        batter["matches"].add(event["match_id"])
        bowler = player_stats[(event["year"], event["bowler"])]
        bowler["bowling_runs_saved"] += expected - event["bowler_conceded"]
        bowler["wickets"] += event["bowler_wickets"]
        bowler["matches"].add(event["match_id"])

    by_season: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for (year, team_id), row in team_stats.items():
        total = row["batting_runs_above_par"] + row["bowling_runs_saved"]
        matches = len(row["matches"])
        by_season[str(year)].append(
            {
                "team": teams[team_id],
                "matches": matches,
                "batting_runs_above_par": round(row["batting_runs_above_par"], 2),
                "bowling_runs_saved": round(row["bowling_runs_saved"], 2),
                "total_runs_above_par": round(total, 2),
                "runs_above_par_per_match": round(total / matches, 2) if matches else 0.0,
                "phases": {
                    phase: {
                        key: round(value, 2)
                        for key, value in row["phases"][phase].items()
                    }
                    for phase in PHASES
                },
            }
        )
    for year, rows in by_season.items():
        values = np.array([row["runs_above_par_per_match"] for row in rows])
        mean, std = float(values.mean()), float(values.std()) or 1.0
        for row in rows:
            row["rating_z"] = round((row["runs_above_par_per_match"] - mean) / std, 3)
        rows.sort(key=lambda row: (-row["rating_z"], row["team"]["name"]))

    players_by_season: dict[str, list[dict[str, Any]]] = defaultdict(list)
    all_player_rows: list[dict[str, Any]] = []
    for (year, player), row in player_stats.items():
        bowling_impact = row["bowling_runs_saved"] + 15.0 * row["wickets"]
        total = row["batting_runs_above_par"] + bowling_impact
        player_row = {
            "player": player,
            "matches": len(row["matches"]),
            "batting_runs_above_par": round(row["batting_runs_above_par"], 2),
            "bowling_runs_saved": round(row["bowling_runs_saved"], 2),
            "bowler_wickets": int(row["wickets"]),
            "bowling_impact_runs": round(bowling_impact, 2),
            "impact_runs": round(total, 2),
        }
        players_by_season[str(year)].append(player_row)
        all_player_rows.append({"season": year, **player_row})
    for year, rows in players_by_season.items():
        rows.sort(key=lambda row: (-row["impact_runs"], row["player"]))
        players_by_season[year] = rows[:25]

    baseline_rows = [
        {
            "season": year,
            "venue": venue,
            "phase": phase,
            "runs_per_ball": round(rate, 5),
        }
        for (year, venue, phase), rate in venue_rates.items()
    ]
    baseline_rows.sort(key=lambda row: (row["season"], row["venue"], PHASES.index(row["phase"])))
    robustness = {
        "schema_version": 1,
        "method": {
            "phases": {"powerplay": "overs 1-6", "middle": "overs 7-15", "death": "overs 16-20"},
            "venue_shrinkage": "Season/venue/phase rate shrunk toward the season/phase mean with a 120-legal-ball prior.",
            "team_value": "Batting runs above par plus equivalent bowling runs saved; independent of Elo.",
        },
        "seasons": dict(sorted(by_season.items())),
        "venue_phase_baselines": baseline_rows,
    }
    players = {
        "schema_version": 1,
        "method": "Batting runs above venue/phase par + bowling runs saved + 15 runs per bowler-credited wicket.",
        "leaderboards": {
            "batting": sorted(
                all_player_rows,
                key=lambda row: (-row["batting_runs_above_par"], row["season"], row["player"]),
            )[:10],
            "bowling": sorted(
                all_player_rows,
                key=lambda row: (-row["bowling_impact_runs"], row["season"], row["player"]),
            )[:10],
        },
        "seasons": dict(sorted(players_by_season.items())),
    }
    return robustness, players


def logistic(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-20.0, min(20.0, value))))


def logit(value: float) -> float:
    clipped = min(0.999, max(0.001, value))
    return math.log(clipped / (1 - clipped))


def expected_remainder(
    year: int,
    venue: str,
    legal_balls: int,
    limit_balls: int,
    global_rates: dict[tuple[int, str], float],
    venue_rates: dict[tuple[int, str, str], float],
) -> float:
    total = 0.0
    for ball_index in range(legal_balls, limit_balls):
        phase = phase_for(ball_index // 6)
        total += venue_rates.get((year, venue, phase), global_rates[(year, phase)])
    return total


def win_probability_trace(
    path: Path,
    year: int,
    pre_probability_team_a: float,
    registry: TeamRegistry,
    global_rates: dict[tuple[int, str], float],
    venue_rates: dict[tuple[int, str, str], float],
) -> dict[str, Any]:
    raw = load_json(path)
    info = raw["info"]
    team_a = registry.resolve(info["teams"][0])
    team_b = registry.resolve(info["teams"][1])
    venue = info.get("venue") or "Unknown venue"
    balls_per_over = int(info.get("balls_per_over", 6))
    quota = int(info.get("overs", 20)) * balls_per_over
    par_total = expected_remainder(year, venue, 0, quota, global_rates, venue_rates)
    states: list[dict[str, Any]] = []
    first_total = None

    for innings_number, innings in enumerate(raw.get("innings", [])[:2], start=1):
        batting = registry.resolve(innings["team"])
        score = wickets = legal_balls = 0
        target_data = innings.get("target", {})
        target = int(target_data.get("runs", (first_total or 0) + 1)) if innings_number == 2 else None
        innings_limit = (
            overs_to_balls(target_data.get("overs", info.get("overs", 20)), balls_per_over)
            if innings_number == 2
            else quota
        )
        for over in innings.get("overs", []):
            for delivery in over.get("deliveries", []):
                extras = delivery.get("extras", {})
                legal = "wides" not in extras and "noballs" not in extras
                score += int(delivery.get("runs", {}).get("total", 0))
                if legal:
                    legal_balls += 1
                wickets += sum(wicket.get("kind") != "retired hurt" for wicket in delivery.get("wickets", []))
                wickets_in_hand = max(0, 10 - wickets)
                wicket_factor = max(0.48, 0.72 + 0.028 * wickets_in_hand)
                if innings_number == 1:
                    projected = score + expected_remainder(
                        year, venue, legal_balls, innings_limit, global_rates, venue_rates
                    ) * wicket_factor
                    batting_advantage = (projected - par_total) / 18.0
                    team_a_probability = logistic(
                        logit(pre_probability_team_a)
                        + (batting_advantage if batting["id"] == team_a["id"] else -batting_advantage)
                    )
                    runs_required = balls_remaining = None
                else:
                    runs_required = max(0, int(target) - score)
                    balls_remaining = max(0, innings_limit - legal_balls)
                    capacity = expected_remainder(
                        year, venue, legal_balls, innings_limit, global_rates, venue_rates
                    ) * wicket_factor
                    chasing_prior = (
                        pre_probability_team_a if batting["id"] == team_a["id"] else 1 - pre_probability_team_a
                    )
                    chase_probability = logistic(logit(chasing_prior) + (capacity - runs_required) / 10.5)
                    team_a_probability = (
                        chase_probability if batting["id"] == team_a["id"] else 1 - chase_probability
                    )
                states.append(
                    {
                        "ball": delivery.get("actual_delivery"),
                        "innings": innings_number,
                        "batting_team_id": batting["id"],
                        "score": score,
                        "wickets": wickets,
                        "runs_required": runs_required,
                        "balls_remaining": balls_remaining,
                        "team_a_win_probability": round(team_a_probability, 4),
                    }
                )
        if innings_number == 1:
            first_total = score

    winner_source = info.get("outcome", {}).get("winner") or info.get("outcome", {}).get("eliminator")
    winner = registry.resolve(winner_source) if winner_source else None
    if states and winner:
        states[-1]["team_a_win_probability"] = 1.0 if winner["id"] == team_a["id"] else 0.0
    changes = [
        abs(states[index]["team_a_win_probability"] - states[index - 1]["team_a_win_probability"])
        for index in range(1, len(states))
    ]
    turning_index = int(np.argmax(changes)) + 1 if changes else 0
    return {
        "season": year,
        "match_id": path.stem,
        "title": f"{team_a['abbr']} v {team_b['abbr']} · {year} Final",
        "date": sorted(info.get("dates", []))[0],
        "venue": venue,
        "team_a": team_a,
        "team_b": team_b,
        "winner": winner,
        "pre_match_probability_team_a": round(pre_probability_team_a, 4),
        "turning_point_index": turning_index,
        "states": states,
    }


def build_famous_matches(
    parsed_dir: Path,
    path_by_id: dict[str, Path],
    elo: dict[str, Any],
    registry: TeamRegistry,
    global_rates: dict[tuple[int, str], float],
    venue_rates: dict[tuple[int, str, str], float],
) -> dict[str, Any]:
    selected_years = [2008, 2009, 2012, 2014, 2016, 2017, 2019, 2023, 2025, 2026]
    matches = []
    scale = float(elo["model"]["elo_scale"])
    for year in selected_years:
        season = load_json(parsed_dir / f"{year}.json")
        final = next(match for match in season["matches"] if match["stage"] == "final")
        ratings = elo["seasons"][str(year)]["league_end"]
        team_a, team_b = final["teams"][0]["id"], final["teams"][1]["id"]
        pre_probability = 1.0 / (1.0 + 10.0 ** (-(ratings[team_a] - ratings[team_b]) / scale))
        matches.append(
            win_probability_trace(
                path_by_id[final["id"]], year, pre_probability, registry, global_rates, venue_rates
            )
        )
    return {
        "schema_version": 1,
        "method": "Resource-state descriptive model using score, balls remaining, wickets in hand, venue/phase par and league-end Elo prior.",
        "matches": matches,
    }


def add_elo_comparison(robustness: dict[str, Any], elo: dict[str, Any]) -> None:
    """Attach rank agreement so the independent model is a measurable robustness check."""
    rows: list[dict[str, Any]] = []
    all_ball: list[float] = []
    all_elo: list[float] = []
    for year, team_rows in robustness["seasons"].items():
        elo_rows = elo["seasons"][year]["league_end"]
        paired = [row for row in team_rows if row["team"]["id"] in elo_rows]
        ball = np.array([row["rating_z"] for row in paired], dtype=float)
        elo_values = np.array([elo_rows[row["team"]["id"]] for row in paired], dtype=float)
        correlation = float(np.corrcoef(ball, elo_values)[0, 1]) if len(paired) > 1 else 0.0
        rows.append({"season": int(year), "teams": len(paired), "correlation": round(correlation, 3)})
        all_ball.extend(ball.tolist())
        all_elo.extend(elo_values.tolist())
    overall = float(np.corrcoef(all_ball, all_elo)[0, 1]) if len(all_ball) > 1 else 0.0
    robustness["comparison_to_elo"] = {
        "metric": "Pearson correlation between season-standardized ball rating and league-end Elo",
        "overall_correlation": round(overall, 3),
        "team_seasons": len(all_ball),
        "by_season": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Extracted Cricsheet IPL JSON root")
    parser.add_argument("--parsed", type=Path, default=ROOT / "data/parsed/seasons")
    parser.add_argument("--output", type=Path, default=ROOT / "data")
    args = parser.parse_args()
    registry = TeamRegistry()
    teams = canonical_by_id(registry)
    events, path_by_id = collect_events(args.input, registry)
    global_rates, venue_rates = build_baselines(events)
    robustness, players = build_robustness(events, global_rates, venue_rates, teams)
    elo = load_json(args.output / "ratings/elo.json")
    add_elo_comparison(robustness, elo)
    famous = build_famous_matches(
        args.parsed, path_by_id, elo, registry, global_rates, venue_rates
    )
    stable_write(args.output / "ratings/robustness.json", robustness)
    stable_write(args.output / "analytics/players.json", players)
    stable_write(args.output / "analytics/famous_matches.json", famous)
    print(
        f"Built robustness from {len(events):,} delivery records; "
        f"{sum(len(rows) for rows in robustness['seasons'].values())} team-seasons; "
        f"{len(famous['matches'])} win-probability matches"
    )


if __name__ == "__main__":
    main()
