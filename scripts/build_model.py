#!/usr/bin/env python3
"""Build calibrated IPL Elo ratings, season simulations and headline analytics."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def stable_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def probability(rating_a: float, rating_b: float, scale: float, home_edge_a: float = 0.0) -> float:
    return 1.0 / (1.0 + 10.0 ** (-((rating_a + home_edge_a) - rating_b) / scale))


def home_team_id(match: dict[str, Any], year: int, home_config: dict[str, Any]) -> str | None:
    if year in home_config["neutral_seasons"] or match["stage"] != "league":
        return None
    venue = match.get("venue") or ""
    participants = {team["id"] for team in match["teams"]}
    for rule in home_config["rules"]:
        if rule["team_id"] not in participants:
            continue
        if "years" in rule and year not in rule["years"]:
            continue
        if any(fragment.lower() in venue.lower() for fragment in rule["venue_contains"]):
            return rule["team_id"]
    return None


def margin_multiplier(match: dict[str, Any]) -> float:
    margin = match["outcome"].get("margin")
    if not margin or match["outcome"]["type"] in {"tie", "super_over_win"}:
        return 1.0
    unit = margin["unit"]
    value = float(margin["value"])
    if unit == "runs":
        return round(1.0 + min(1.25, math.log1p(value) / math.log(51.0)), 6)
    if unit == "wickets":
        chase = match["innings"][1] if len(match.get("innings", [])) > 1 else None
        quota = float(match.get("scheduled_overs", 20) * match.get("balls_per_over", 6))
        balls_remaining = max(0.0, quota - float(chase["legal_balls"])) if chase else 0.0
        weight = 0.65 * (value / 10.0) + 0.60 * (balls_remaining / max(quota, 1.0))
        return round(1.0 + min(1.25, weight), 6)
    return 1.0


def match_score(match: dict[str, Any]) -> float | None:
    winner = match["outcome"].get("winner")
    if winner:
        return 1.0 if winner["id"] == match["teams"][0]["id"] else 0.0
    if match["outcome"]["type"] == "tie":
        return 0.5
    return None


def season_paths(parsed_dir: Path) -> list[Path]:
    return sorted(parsed_dir.glob("20*.json"), key=lambda path: int(path.stem))


def run_elo(
    seasons: list[dict[str, Any]],
    model: dict[str, Any],
    home_config: dict[str, Any],
    scale: float,
    home_advantage: float,
    k_factor: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    base = float(model["base_rating"])
    mega_years = set(model["mega_auction_years"])
    ratings: dict[str, float] = {}
    last_edges: dict[str, float] = {}
    history: dict[str, Any] = {}
    predictions: list[dict[str, Any]] = []

    for season in seasons:
        year = int(season["season"])
        active = [row["team"] for row in season["actual_table"]]
        active_ids = [team["id"] for team in active]
        carryover = float(
            model["mega_auction_carryover"] if year in mega_years else model["normal_carryover"]
        )
        start_ratings: dict[str, float] = {}
        for team_id in active_ids:
            if team_id in last_edges:
                start_ratings[team_id] = base + carryover * last_edges[team_id]
            else:
                start_ratings[team_id] = base - float(model["expansion_penalty"])
        ratings.update(start_ratings)
        match_rows: list[dict[str, Any]] = []

        def process(matches: Iterable[dict[str, Any]]) -> None:
            for match in matches:
                if not match.get("counts_for_table", True):
                    continue
                team_a, team_b = match["teams"][0]["id"], match["teams"][1]["id"]
                home_id = home_team_id(match, year, home_config)
                home_edge = home_advantage if home_id == team_a else -home_advantage if home_id == team_b else 0.0
                rating_a, rating_b = ratings[team_a], ratings[team_b]
                p_a = probability(rating_a, rating_b, scale, home_edge)
                score = match_score(match)
                mov = margin_multiplier(match)
                update = 0.0
                if score is not None and match.get("elo_eligible", False):
                    update = k_factor * mov * (score - p_a)
                    ratings[team_a] += update
                    ratings[team_b] -= update
                    predictions.append(
                        {
                            "season": year,
                            "match_id": match["id"],
                            "probability_a": p_a,
                            "score_a": score,
                        }
                    )
                match_rows.append(
                    {
                        "match_id": match["id"],
                        "date": match["date"],
                        "stage": match["stage"],
                        "team_a": team_a,
                        "team_b": team_b,
                        "rating_a_before": round(rating_a, 3),
                        "rating_b_before": round(rating_b, 3),
                        "probability_a": round(p_a, 6),
                        "home_team_id": home_id,
                        "margin_multiplier": mov,
                        "score_a": score,
                        "elo_update_a": round(update, 3),
                        "rating_a_after": round(ratings[team_a], 3),
                        "rating_b_after": round(ratings[team_b], 3),
                    }
                )

        league = [match for match in season["matches"] if match["stage"] == "league"]
        playoffs = [match for match in season["matches"] if match["stage"] != "league"]
        process(league)
        league_end = {team_id: round(ratings[team_id], 3) for team_id in active_ids}
        process(playoffs)
        season_end = {team_id: round(ratings[team_id], 3) for team_id in active_ids}
        season_mean = float(np.mean([ratings[team_id] for team_id in active_ids]))
        for team_id in active_ids:
            last_edges[team_id] = ratings[team_id] - season_mean
        history[str(year)] = {
            "carryover": carryover,
            "mega_auction": year in mega_years,
            "start": {key: round(value, 3) for key, value in start_ratings.items()},
            "league_end": league_end,
            "season_end": season_end,
            "matches": match_rows,
        }
    return history, predictions


def calibrate(
    seasons: list[dict[str, Any]], model: dict[str, Any], home_config: dict[str, Any]
) -> tuple[float, float, float, list[dict[str, Any]]]:
    results: list[dict[str, Any]] = []
    holdout = int(model["calibration_holdout_start"])
    for k_factor in model["k_factor_candidates"]:
        for scale in model["elo_scale_candidates"]:
            for home in model["home_advantage_candidates"]:
                history, _ = run_elo(
                    seasons, model, home_config, float(scale), float(home), float(k_factor)
                )
                observed: list[tuple[float, float]] = []
                for season in seasons:
                    year = int(season["season"])
                    if year < holdout:
                        continue
                    end_ratings = history[str(year)]["league_end"]
                    records = {row["match_id"]: row for row in history[str(year)]["matches"]}
                    for match in season["matches"]:
                        score = match_score(match)
                        if (
                            match["stage"] != "league"
                            or not match.get("counts_for_table", True)
                            or score not in (0.0, 1.0)
                        ):
                            continue
                        team_a, team_b = match["teams"][0]["id"], match["teams"][1]["id"]
                        home_id = records[match["id"]]["home_team_id"]
                        home_edge = (
                            float(home)
                            if home_id == team_a
                            else -float(home)
                            if home_id == team_b
                            else 0.0
                        )
                        p_a = probability(
                            end_ratings[team_a], end_ratings[team_b], float(scale), home_edge
                        )
                        observed.append((p_a, score))
                probs = np.array([row[0] for row in observed], dtype=float)
                scores = np.array([row[1] for row in observed], dtype=float)
                clipped = np.clip(probs, 1e-9, 1 - 1e-9)
                log_loss = float(-np.mean(scores * np.log(clipped) + (1 - scores) * np.log(1 - clipped)))
                brier = float(np.mean((probs - scores) ** 2))
                results.append(
                    {
                        "k_factor": int(k_factor),
                        "scale": int(scale),
                        "home_advantage": int(home),
                        "matches": len(observed),
                        "log_loss": round(log_loss, 6),
                        "brier_score": round(brier, 6),
                    }
                )
    results.sort(
        key=lambda row: (
            row["log_loss"], row["brier_score"], row["scale"], row["k_factor"], row["home_advantage"]
        )
    )
    winner = results[0]
    return float(winner["scale"]), float(winner["home_advantage"]), float(winner["k_factor"]), results


def paired_winner(
    left: np.ndarray,
    right: np.ndarray,
    ratings: np.ndarray,
    scale: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    probs = 1.0 / (1.0 + 10.0 ** (-(ratings[left] - ratings[right]) / scale))
    left_wins = rng.random(left.shape[0]) < probs
    return np.where(left_wins, left, right), np.where(left_wins, right, left)


def simulate_season(
    season: dict[str, Any],
    elo: dict[str, Any],
    model: dict[str, Any],
    scale: float,
) -> dict[str, Any]:
    year = int(season["season"])
    simulations = int(model["simulation_count"])
    seed = int(model["seed_base"]) + year
    rng = np.random.default_rng(seed)
    team_rows = season["actual_table"]
    team_ids = [row["team"]["id"] for row in team_rows]
    team_lookup = {row["team"]["id"]: row["team"] for row in team_rows}
    index = {team_id: position for position, team_id in enumerate(team_ids)}
    team_count = len(team_ids)
    points = np.zeros((simulations, team_count), dtype=np.int16)
    wins = np.zeros((simulations, team_count), dtype=np.int16)
    margin_proxy = np.zeros((simulations, team_count), dtype=np.float32)
    elo_matches = {row["match_id"]: row for row in elo["matches"]}
    fixtures: list[dict[str, Any]] = []

    for match in season["matches"]:
        if match["stage"] != "league" or not match.get("counts_for_table", True):
            continue
        team_a, team_b = match["teams"][0]["id"], match["teams"][1]["id"]
        a, b = index[team_a], index[team_b]
        rating_row = elo_matches[match["id"]]
        home_id = rating_row["home_team_id"]
        home_edge = (
            float(elo["home_advantage"])
            if home_id == team_a
            else -float(elo["home_advantage"])
            if home_id == team_b
            else 0.0
        )
        p_a = probability(
            float(elo["league_end"][team_a]),
            float(elo["league_end"][team_b]),
            scale,
            home_edge,
        )
        no_result = match["outcome"]["type"] in {"no_result", "abandoned"}
        actual_winner = match["outcome"]["winner"]["id"] if match["outcome"].get("winner") else None
        fixtures.append(
            {
                "id": match["id"],
                "date": match["date"],
                "team_a": team_a,
                "team_b": team_b,
                "probability_a": round(p_a, 6),
                "actual_winner": actual_winner,
                "no_result": no_result,
                "home_team_id": rating_row["home_team_id"],
            }
        )
        if no_result:
            points[:, a] += 1
            points[:, b] += 1
            continue
        a_wins = rng.random(simulations) < p_a
        points[:, a] += a_wins.astype(np.int16) * 2
        points[:, b] += (~a_wins).astype(np.int16) * 2
        wins[:, a] += a_wins.astype(np.int16)
        wins[:, b] += (~a_wins).astype(np.int16)
        magnitude = 0.2 + abs(p_a - 0.5) + rng.gamma(shape=1.8, scale=0.25, size=simulations)
        signed = np.where(a_wins, magnitude, -magnitude)
        margin_proxy[:, a] += signed
        margin_proxy[:, b] -= signed

    jitter = rng.random((simulations, team_count)) * 1e-6
    order = np.lexsort((jitter, -margin_proxy, -wins, -points), axis=1)
    positions = np.empty_like(order)
    positions[np.arange(simulations)[:, None], order] = np.arange(1, team_count + 1)
    top_four = order[:, :4]
    league_ratings = np.array([float(elo["league_end"][team_id]) for team_id in team_ids])

    if season["config"]["playoff_format"] == "two_semifinals_final":
        semi_one_winner, _ = paired_winner(top_four[:, 0], top_four[:, 3], league_ratings, scale, rng)
        semi_two_winner, _ = paired_winner(top_four[:, 1], top_four[:, 2], league_ratings, scale, rng)
        champion, runner_up = paired_winner(semi_one_winner, semi_two_winner, league_ratings, scale, rng)
    else:
        qualifier_winner, qualifier_loser = paired_winner(top_four[:, 0], top_four[:, 1], league_ratings, scale, rng)
        eliminator_winner, _ = paired_winner(top_four[:, 2], top_four[:, 3], league_ratings, scale, rng)
        qualifier_two_winner, _ = paired_winner(qualifier_loser, eliminator_winner, league_ratings, scale, rng)
        champion, runner_up = paired_winner(qualifier_winner, qualifier_two_winner, league_ratings, scale, rng)

    final_counts = np.bincount(np.concatenate([champion, runner_up]), minlength=team_count)
    champion_counts = np.bincount(champion, minlength=team_count)
    playoff_counts = np.bincount(top_four.ravel(), minlength=team_count)
    finals = [match for match in season["matches"] if match["stage"] == "final" and match["outcome"].get("winner")]
    actual_champion_id = sorted(finals, key=lambda match: match["date"] or "")[-1]["outcome"]["winner"]["id"]
    actual_by_id = {row["team"]["id"]: row for row in team_rows}
    output_teams: list[dict[str, Any]] = []
    for team_id, idx in index.items():
        values, counts = np.unique(points[:, idx], return_counts=True)
        position_counts = np.bincount(positions[:, idx], minlength=team_count + 1)[1:]
        actual = actual_by_id[team_id]
        median_points = float(np.median(points[:, idx]))
        output_teams.append(
            {
                "team": team_lookup[team_id],
                "actual_points": actual["points"],
                "actual_position": actual["position"],
                "expected_points": round(float(np.mean(points[:, idx])), 2),
                "median_points": median_points,
                "expected_position": round(float(np.mean(positions[:, idx])), 2),
                "luck_index": round(float(actual["points"] - median_points), 2),
                "playoff_probability": round(float(playoff_counts[idx] / simulations), 4),
                "final_probability": round(float(final_counts[idx] / simulations), 4),
                "title_probability": round(float(champion_counts[idx] / simulations), 4),
                "points_distribution": {str(int(value)): int(count) for value, count in zip(values, counts)},
                "position_distribution": {str(pos): int(count) for pos, count in enumerate(position_counts, 1)},
                "league_end_elo": float(elo["league_end"][team_id]),
            }
        )
    output_teams.sort(key=lambda row: row["actual_position"])
    champion_row = next(row for row in output_teams if row["team"]["id"] == actual_champion_id)
    robbery_row = max(
        (row for row in output_teams if row["team"]["id"] != actual_champion_id),
        key=lambda row: row["title_probability"],
    )
    best_rating = max(league_ratings)
    best_index = int(np.argmax(league_ratings))
    field_mean = float(np.mean(np.delete(league_ratings, best_index)))
    return {
        "schema_version": 1,
        "season": year,
        "seed": seed,
        "simulation_count": simulations,
        "model": {
            "elo_scale": scale,
            "home_advantage": elo["home_advantage"],
            "playoff_format": season["config"]["playoff_format"],
            "no_result_policy": model["no_result_policy"],
            "nrr_policy": model["nrr_policy"],
        },
        "actual_champion": team_lookup[actual_champion_id],
        "champion_title_probability": champion_row["title_probability"],
        "fluke_score": round(1.0 - champion_row["title_probability"], 4),
        "robbery": {
            "team": robbery_row["team"],
            "title_probability": robbery_row["title_probability"],
        },
        "dominance": {
            "team": team_lookup[team_ids[best_index]],
            "elo_gap_to_field": round(float(best_rating - field_mean), 2),
        },
        "fixtures": fixtures,
        "teams": output_teams,
    }


def close_games(season: dict[str, Any], elo: dict[str, Any]) -> list[dict[str, Any]]:
    records = {row["match_id"]: row for row in elo["matches"]}
    totals: dict[str, dict[str, float]] = defaultdict(lambda: {"played": 0, "won": 0, "expected_wins": 0.0})
    for match in season["matches"]:
        if match["stage"] != "league" or not match.get("elo_eligible"):
            continue
        margin = match["outcome"].get("margin")
        if not margin:
            continue
        is_close = (margin["unit"] == "runs" and margin["value"] < 10) or (
            margin["unit"] == "wickets" and margin["value"] < 3
        )
        if not is_close:
            continue
        record = records[match["id"]]
        for team_key, probability_key in (("team_a", "probability_a"), ("team_b", "probability_b")):
            team_id = record[team_key]
            p = record["probability_a"] if probability_key == "probability_a" else 1 - record["probability_a"]
            totals[team_id]["played"] += 1
            totals[team_id]["expected_wins"] += p
            if match["outcome"]["winner"]["id"] == team_id:
                totals[team_id]["won"] += 1
    output = []
    for team_id, row in totals.items():
        output.append(
            {
                "team_id": team_id,
                "played": int(row["played"]),
                "won": int(row["won"]),
                "expected_wins": round(row["expected_wins"], 2),
                "overperformance": round(row["won"] - row["expected_wins"], 2),
            }
        )
    return sorted(output, key=lambda row: (-row["overperformance"], row["team_id"]))


def runs_test(sequence: list[int]) -> dict[str, Any] | None:
    ones, zeros = sum(sequence), len(sequence) - sum(sequence)
    if ones == 0 or zeros == 0 or len(sequence) < 4:
        return None
    runs = 1 + sum(left != right for left, right in zip(sequence, sequence[1:]))
    expected = 1 + 2 * ones * zeros / (ones + zeros)
    variance = 2 * ones * zeros * (2 * ones * zeros - ones - zeros) / (((ones + zeros) ** 2) * (ones + zeros - 1))
    z_score = (runs - expected) / math.sqrt(variance) if variance > 0 else 0.0
    return {"games": len(sequence), "runs": runs, "expected_runs": round(expected, 3), "z_score": round(z_score, 3)}


def momentum_analysis(seasons: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for season in seasons:
        sequences: dict[str, list[int]] = defaultdict(list)
        for match in season["matches"]:
            if match["stage"] != "league" or not match.get("elo_eligible") or not match["outcome"].get("winner"):
                continue
            winner = match["outcome"]["winner"]["id"]
            for team in match["teams"]:
                sequences[team["id"]].append(int(team["id"] == winner))
        for team_id, sequence in sequences.items():
            test = runs_test(sequence)
            if test:
                rows.append({"season": season["season"], "team_id": team_id, **test})
    significant = sum(abs(row["z_score"]) >= 1.96 for row in rows)
    return {
        "test": "Wald-Wolfowitz runs test",
        "team_seasons_tested": len(rows),
        "significant_at_5pct": significant,
        "significant_share": round(significant / len(rows), 4) if rows else 0,
        "rows": rows,
    }


def venue_analysis(seasons: list[dict[str, Any]]) -> list[dict[str, Any]]:
    venues: dict[str, dict[str, int]] = defaultdict(lambda: {"matches": 0, "chase_wins": 0, "field_tosses": 0, "field_toss_wins": 0})
    for season in seasons:
        for match in season["matches"]:
            if match["stage"] != "league" or len(match.get("innings", [])) < 2 or not match["outcome"].get("winner"):
                continue
            venue = match.get("venue") or "Unknown venue"
            row = venues[venue]
            row["matches"] += 1
            chase_team = match["innings"][1]["team"]["id"]
            if match["outcome"]["winner"]["id"] == chase_team:
                row["chase_wins"] += 1
            toss = match.get("toss", {})
            if toss.get("decision") == "field" and toss.get("winner"):
                row["field_tosses"] += 1
                if toss["winner"]["id"] == match["outcome"]["winner"]["id"]:
                    row["field_toss_wins"] += 1
    output = []
    for venue, row in venues.items():
        output.append(
            {
                "venue": venue,
                **row,
                "chase_win_rate": round(row["chase_wins"] / row["matches"], 4),
                "field_toss_win_rate": round(row["field_toss_wins"] / row["field_tosses"], 4) if row["field_tosses"] else None,
            }
        )
    return sorted(output, key=lambda row: (-row["matches"], row["venue"]))


def regression_analysis(elo_history: dict[str, Any]) -> dict[str, Any]:
    pairs = []
    years = sorted(map(int, elo_history))
    for previous, current in zip(years, years[1:]):
        previous_ratings = elo_history[str(previous)]["league_end"]
        current_ratings = elo_history[str(current)]["league_end"]
        for team_id in sorted(set(previous_ratings) & set(current_ratings)):
            pairs.append(
                {
                    "from_season": previous,
                    "to_season": current,
                    "team_id": team_id,
                    "rating_from": previous_ratings[team_id],
                    "rating_to": current_ratings[team_id],
                }
            )
    x = np.array([row["rating_from"] for row in pairs])
    y = np.array([row["rating_to"] for row in pairs])
    correlation = float(np.corrcoef(x, y)[0, 1]) if len(pairs) > 1 else 0.0
    slope = float(np.polyfit(x - 1500, y - 1500, 1)[0]) if len(pairs) > 1 else 0.0
    return {"pairs": len(pairs), "correlation": round(correlation, 3), "persistence_slope": round(slope, 3)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parsed", type=Path, default=ROOT / "data/parsed/seasons")
    parser.add_argument("--output", type=Path, default=ROOT / "data")
    args = parser.parse_args()
    model = load_json(ROOT / "config/model.json")
    home_config = load_json(ROOT / "config/home_venues.json")
    seasons = [load_json(path) for path in season_paths(args.parsed)]
    expected_years = list(range(2008, 2027))
    if [season["season"] for season in seasons] != expected_years:
        raise SystemExit("Parsed seasons must cover every IPL edition from 2008 through 2026")

    scale, home_advantage, k_factor, calibration_grid = calibrate(seasons, model, home_config)
    coin_flip_log_loss = round(math.log(2), 6)
    if calibration_grid[0]["log_loss"] >= coin_flip_log_loss:
        raise SystemExit(
            "Calibration failed: the selected retrospective Elo model does not beat a 50/50 baseline"
        )
    elo_history, predictions = run_elo(seasons, model, home_config, scale, home_advantage, k_factor)
    for season_data in elo_history.values():
        season_data["home_advantage"] = home_advantage
    calibration = {
        "schema_version": 1,
        "selection_metric": "retrospective league-end Elo holdout log loss",
        "holdout_seasons": [int(model["calibration_holdout_start"]), 2026],
        "selected": {"elo_scale": scale, "home_advantage": home_advantage, "k_factor": k_factor},
        "coin_flip_log_loss": coin_flip_log_loss,
        "interpretation": "Retrospective season-strength model for counterfactual replay, not a pre-match forecasting claim.",
        "grid": calibration_grid,
    }
    stable_write(args.output / "ratings/calibration.json", calibration)
    stable_write(
        args.output / "ratings/elo.json",
        {
            "schema_version": 1,
            "model": {
                "base_rating": model["base_rating"],
                "expansion_penalty": model["expansion_penalty"],
                "k_factor": k_factor,
                "elo_scale": scale,
                "home_advantage": home_advantage,
                "mega_auction_years": model["mega_auction_years"],
                "mega_auction_carryover": model["mega_auction_carryover"],
                "normal_carryover": model["normal_carryover"],
                "margin_multiplier": {
                    "run_win": "1 + min(1.25, ln(1 + margin_runs) / ln(51))",
                    "wicket_win": "1 + min(1.25, 0.65*wickets/10 + 0.60*balls_remaining/quota)",
                },
            },
            "seasons": elo_history,
        },
    )

    simulations = []
    close_game_rows = []
    for season in seasons:
        year = str(season["season"])
        simulation = simulate_season(season, elo_history[year], model, scale)
        stable_write(args.output / f"simulations/{year}.json", simulation)
        simulations.append(simulation)
        close_game_rows.append({"season": int(year), "teams": close_games(season, elo_history[year])})

    season_summaries = [
        {
            "season": item["season"],
            "champion": item["actual_champion"],
            "champion_title_probability": item["champion_title_probability"],
            "fluke_score": item["fluke_score"],
            "robbery": item["robbery"],
            "dominance": item["dominance"],
        }
        for item in simulations
    ]
    stable_write(
        args.output / "analytics/index.json",
        {
            "schema_version": 1,
            "seasons": season_summaries,
            "flukiest_champions": sorted(season_summaries, key=lambda row: (-row["fluke_score"], row["season"])),
            "biggest_robberies": sorted(season_summaries, key=lambda row: (-row["robbery"]["title_probability"], row["season"])),
            "most_dominant": sorted(season_summaries, key=lambda row: (-row["dominance"]["elo_gap_to_field"], row["season"])),
            "close_games": close_game_rows,
            "momentum": momentum_analysis(seasons),
            "toss_dew_proxy": venue_analysis(seasons),
            "regression_to_mean": regression_analysis(elo_history),
        },
    )
    stable_write(
        args.output / "analytics/what_if.json",
        {
            "schema_version": 1,
            "simulation_count": int(model["client_simulation_count"]),
            "elo_scale": scale,
            "home_advantage": home_advantage,
            "mega_auction_years": model["mega_auction_years"],
            "mega_auction_carryover": model["mega_auction_carryover"],
            "normal_carryover": model["normal_carryover"],
            "seasons": {
                str(item["season"]): {
                    "seed": item["seed"] + 700_000,
                    "playoff_format": item["model"]["playoff_format"],
                    "teams": [
                        {
                            "team": row["team"],
                            "rating": row["league_end_elo"],
                            "actual_points": row["actual_points"],
                            "actual_position": row["actual_position"],
                        }
                        for row in item["teams"]
                    ],
                    "fixtures": item["fixtures"],
                }
                for item in simulations
            },
        },
    )
    print(
        f"Built Elo and {len(simulations)} x {model['simulation_count']:,} simulations "
        f"with scale={scale:g}, home={home_advantage:g}, K={k_factor:g}; {len(predictions)} rated matches"
    )


if __name__ == "__main__":
    main()
