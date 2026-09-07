#!/usr/bin/env python3
"""Parse Cricsheet IPL JSON into deterministic, site-ready season artifacts."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
NON_BOWLER_WICKETS = {"retired hurt", "retired out", "obstructing the field"}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def stable_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    path.write_text(rendered, encoding="utf-8")


def season_year(value: Any) -> int:
    text = str(value)
    match = re.search(r"(?:19|20)\d{2}", text)
    if not match:
        raise ValueError(f"Unrecognised season label: {value!r}")
    first_year = int(match.group())
    # Cricsheet labels the inaugural edition 2007/08; the IPL season is 2008.
    return 2008 if text == "2007/08" else first_year


class TeamRegistry:
    def __init__(self, config_path: Path = CONFIG_DIR / "teams.json") -> None:
        config = load_json(config_path)
        self.aliases: dict[str, dict[str, str]] = config["aliases"]
        self.lineage_notes: list[str] = config["lineage_notes"]

    def resolve(self, source_name: str) -> dict[str, str]:
        try:
            team = self.aliases[source_name]
        except KeyError as exc:
            raise ValueError(f"Unknown IPL team alias: {source_name!r}") from exc
        return {"id": team["id"], "name": team["name"], "abbr": team["abbr"]}


def iter_match_paths(input_path: Path, wanted_year: int | None) -> Iterable[Path]:
    candidates = sorted(input_path.rglob("*.json"))
    if not candidates:
        raise FileNotFoundError(f"No JSON matches found below {input_path}")
    for path in candidates:
        try:
            info = load_json(path).get("info", {})
            year = season_year(info.get("season", path.parent.name))
        except (json.JSONDecodeError, ValueError):
            continue
        if wanted_year is None or year == wanted_year:
            yield path


def stage_for(info: dict[str, Any]) -> str:
    event = info.get("event", {})
    raw = str(event.get("stage") or event.get("match_number") or "").lower()
    if "final" in raw and "semi" not in raw:
        return "final"
    if "semi" in raw:
        return "semi_final"
    if "qualifier" in raw:
        number = re.search(r"\d+", raw)
        return f"qualifier_{number.group()}" if number else "qualifier"
    if "eliminator" in raw:
        return "eliminator"
    return "league"


def innings_summary(innings: dict[str, Any]) -> dict[str, Any]:
    runs = 0
    wickets = 0
    legal_balls = 0
    boundaries = {"fours": 0, "sixes": 0}
    for over in innings.get("overs", []):
        for delivery in over.get("deliveries", []):
            delivery_runs = delivery.get("runs", {})
            runs += int(delivery_runs.get("total", 0))
            batter_runs = int(delivery_runs.get("batter", 0))
            boundaries["fours"] += int(batter_runs == 4)
            boundaries["sixes"] += int(batter_runs == 6)
            extras = delivery.get("extras", {})
            if "wides" not in extras and "noballs" not in extras:
                legal_balls += 1
            for wicket in delivery.get("wickets", []):
                if wicket.get("kind") not in NON_BOWLER_WICKETS:
                    wickets += 1
    return {
        "team_source": innings.get("team"),
        "runs": runs,
        "wickets": wickets,
        "legal_balls": legal_balls,
        "overs": f"{legal_balls // 6}.{legal_balls % 6}",
        "boundaries": boundaries,
        "declared": bool(innings.get("declared", False)),
        "forfeited": bool(innings.get("forfeited", False)),
        "target": innings.get("target"),
    }


def parse_outcome(raw: dict[str, Any], registry: TeamRegistry) -> dict[str, Any]:
    winner_source = raw.get("winner") or raw.get("eliminator") or raw.get("bowl_out")
    winner = registry.resolve(winner_source) if winner_source else None
    result = raw.get("result")
    if winner:
        result_type = "super_over_win" if raw.get("eliminator") else "win"
    elif result == "tie":
        result_type = "tie"
    elif result == "no result":
        result_type = "no_result"
    else:
        result_type = "abandoned"
    by = raw.get("by", {})
    margin = None
    for unit in ("runs", "wickets", "innings"):
        if unit in by:
            margin = {"value": int(by[unit]), "unit": unit}
            break
    return {
        "type": result_type,
        "winner": winner,
        "margin": margin,
        "method": raw.get("method"),
    }


def parse_match(path: Path, registry: TeamRegistry) -> dict[str, Any]:
    raw = load_json(path)
    info = raw["info"]
    event = info.get("event", {})
    teams = [registry.resolve(name) for name in info["teams"]]
    toss = info.get("toss", {})
    innings = [innings_summary(value) for value in raw.get("innings", [])]
    for summary in innings:
        team = registry.resolve(summary.pop("team_source"))
        summary["team"] = team
    outcome = parse_outcome(info.get("outcome", {}), registry)
    return {
        "id": path.stem,
        "date": sorted(info.get("dates", []))[0] if info.get("dates") else None,
        "city": info.get("city"),
        "venue": info.get("venue"),
        "stage": stage_for(info),
        "match_number": event.get("match_number") or event.get("stage"),
        "teams": teams,
        "toss": {
            "winner": registry.resolve(toss["winner"]) if toss.get("winner") else None,
            "decision": toss.get("decision"),
        },
        "outcome": outcome,
        "innings": innings,
        "balls_per_over": int(info.get("balls_per_over", 6)),
        "scheduled_overs": int(info.get("overs", 20)),
        "elo_eligible": outcome["type"] in {"win", "super_over_win", "tie"},
        "source_kind": "cricsheet_ball_by_ball",
    }


def supplemental_match(raw: dict[str, Any], registry: TeamRegistry, defaults: dict[str, Any]) -> dict[str, Any]:
    """Build a configured fixture that has no Cricsheet file because no ball was bowled."""
    teams = [registry.resolve(name) for name in raw["teams"]]
    return {
        "id": str(raw["id"]),
        "date": raw["date"],
        "city": raw.get("city"),
        "venue": raw.get("venue"),
        "stage": raw.get("stage", "league"),
        "match_number": raw.get("match_number"),
        "teams": teams,
        "toss": {"winner": None, "decision": None},
        "outcome": {"type": raw["outcome"], "winner": None, "margin": None, "method": None},
        "innings": [],
        "balls_per_over": 6,
        "scheduled_overs": int(defaults["scheduled_overs"]),
        "elo_eligible": False,
        "source_kind": "season_config_supplement",
        "source_note": raw["reason"],
    }


def actual_table(matches: list[dict[str, Any]], season_config: dict[str, Any]) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    defaults = season_config["defaults"]

    def row_for(team: dict[str, str]) -> dict[str, Any]:
        if team["id"] not in rows:
            rows[team["id"]] = {
                "team": team,
                "played": 0,
                "won": 0,
                "lost": 0,
                "tied": 0,
                "no_result": 0,
                "points": 0,
                "runs_for": 0,
                "balls_for": 0,
                "runs_against": 0,
                "balls_against": 0,
            }
        return rows[team["id"]]

    for match in matches:
        if match["stage"] != "league":
            continue
        left, right = match["teams"]
        left_row, right_row = row_for(left), row_for(right)
        outcome = match["outcome"]
        if outcome["type"] == "abandoned" and not match["innings"]:
            continue
        left_row["played"] += 1
        right_row["played"] += 1
        winner_id = outcome["winner"]["id"] if outcome["winner"] else None
        if winner_id:
            win_row = left_row if left["id"] == winner_id else right_row
            loss_row = right_row if left["id"] == winner_id else left_row
            win_row["won"] += 1
            loss_row["lost"] += 1
            win_row["points"] += defaults["win_points"]
            loss_row["points"] += defaults["loss_points"]
        elif outcome["type"] == "tie":
            left_row["tied"] += 1
            right_row["tied"] += 1
            left_row["points"] += defaults["no_result_points"]
            right_row["points"] += defaults["no_result_points"]
        else:
            left_row["no_result"] += 1
            right_row["no_result"] += 1
            left_row["points"] += defaults["no_result_points"]
            right_row["points"] += defaults["no_result_points"]

        # Only completed two-innings games contribute to NRR.
        if len(match["innings"]) < 2 or outcome["type"] in {"no_result", "abandoned"}:
            continue
        summaries = match["innings"][:2]
        by_id = {value["team"]["id"]: value for value in summaries}
        if left["id"] not in by_id or right["id"] not in by_id:
            continue
        quota = int(match["scheduled_overs"]) * int(match["balls_per_over"])
        # Under NRR rules, a D/L-adjusted first innings is target minus one,
        # scored across the revised chase allocation.
        dls_first_runs = None
        dls_first_balls = None
        chase_target = summaries[1].get("target")
        if match["outcome"].get("method") in {"D/L", "DLS"} and chase_target:
            dls_first_runs = int(chase_target["runs"]) - 1
            dls_first_balls = int(float(chase_target["overs"]) * int(match["balls_per_over"]))
        first_team_id = summaries[0]["team"]["id"]
        for own, opponent in ((left, right), (right, left)):
            own_innings, opp_innings = by_id[own["id"]], by_id[opponent["id"]]
            own_row = row_for(own)
            own_balls = quota if own_innings["wickets"] >= 10 else own_innings["legal_balls"]
            opp_balls = quota if opp_innings["wickets"] >= 10 else opp_innings["legal_balls"]
            own_runs = own_innings["runs"]
            opp_runs = opp_innings["runs"]
            if dls_first_runs is not None and own["id"] == first_team_id:
                own_runs, own_balls = dls_first_runs, dls_first_balls
            if dls_first_runs is not None and opponent["id"] == first_team_id:
                opp_runs, opp_balls = dls_first_runs, dls_first_balls
            own_row["runs_for"] += own_runs
            own_row["balls_for"] += own_balls
            own_row["runs_against"] += opp_runs
            own_row["balls_against"] += opp_balls

    table = []
    for row in rows.values():
        rate_for = row["runs_for"] * 6 / row["balls_for"] if row["balls_for"] else 0.0
        rate_against = row["runs_against"] * 6 / row["balls_against"] if row["balls_against"] else 0.0
        row["net_run_rate"] = round(rate_for - rate_against, 3)
        table.append(row)
    table.sort(key=lambda row: (-row["points"], -row["net_run_rate"], row["team"]["name"]))
    for index, row in enumerate(table, start=1):
        row["position"] = index
    return table


def parse_season(paths: list[Path], year: int, registry: TeamRegistry, configs: dict[str, Any]) -> dict[str, Any]:
    if str(year) not in configs["seasons"]:
        raise ValueError(f"No season config for {year}")
    matches = [parse_match(path, registry) for path in paths]
    season_only_config = configs["seasons"][str(year)]
    matches.extend(
        supplemental_match(value, registry, configs["defaults"])
        for value in season_only_config.get("supplemental_fixtures", [])
    )
    matches.sort(key=lambda value: (value["date"] or "", value["id"]))
    season_config = {
        "defaults": configs["defaults"],
        **configs["seasons"][str(year)],
    }
    stages: dict[str, int] = defaultdict(int)
    for match in matches:
        stages[match["stage"]] += 1
    return {
        "schema_version": 1,
        "season": year,
        "source": {
            "provider": "Cricsheet",
            "format": "JSON",
            "data_version": "1.2.x",
            "files": len(paths),
            "configured_supplements": len(season_only_config.get("supplemental_fixtures", [])),
        },
        "config": season_config,
        "summary": {
            "matches": len(matches),
            "league_matches": stages.get("league", 0),
            "playoff_matches": len(matches) - stages.get("league", 0),
            "stages": dict(sorted(stages.items())),
        },
        "team_identity_notes": registry.lineage_notes,
        "actual_table": actual_table(matches, season_config),
        "matches": matches,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Cricsheet IPL JSON root")
    parser.add_argument("--output", type=Path, required=True, help="Output directory")
    parser.add_argument("--season", type=int, help="Only parse one IPL season")
    args = parser.parse_args()

    registry = TeamRegistry()
    configs = load_json(CONFIG_DIR / "seasons.json")
    grouped: dict[int, list[Path]] = defaultdict(list)
    for path in iter_match_paths(args.input.expanduser().resolve(), args.season):
        raw = load_json(path)
        grouped[season_year(raw["info"]["season"])].append(path)
    if not grouped:
        raise SystemExit(f"No matches found for season {args.season}")
    for year, paths in sorted(grouped.items()):
        artifact = parse_season(sorted(paths), year, registry, configs)
        output_path = args.output / f"{year}.json"
        stable_write(output_path, artifact)
        source_count = artifact["source"]["files"]
        total_count = artifact["summary"]["matches"]
        print(f"{year}: {source_count} source files, {total_count} scheduled matches -> {output_path}")


if __name__ == "__main__":
    main()
