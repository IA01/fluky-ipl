#!/usr/bin/env python3
"""Validate every baked artifact and write a compact machine-readable audit report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_MATCHES = {
    2008: 59, 2009: 59, 2010: 60, 2011: 74, 2012: 76, 2013: 76,
    2014: 60, 2015: 60, 2016: 60, 2017: 60, 2018: 60, 2019: 60,
    2020: 60, 2021: 60, 2022: 74, 2023: 74, 2024: 74, 2025: 74, 2026: 74,
}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    reports = []
    for year, expected_matches in EXPECTED_MATCHES.items():
        parsed = load(ROOT / f"data/parsed/seasons/{year}.json")
        simulation = load(ROOT / f"data/simulations/{year}.json")
        assert parsed["validation"]["status"] == "passed"
        assert parsed["summary"]["matches"] == expected_matches
        assert simulation["simulation_count"] == 10_000
        assert len(parsed["actual_table"]) == len(simulation["teams"])
        assert abs(sum(row["title_probability"] for row in simulation["teams"]) - 1) <= 0.002
        assert abs(sum(row["playoff_probability"] for row in simulation["teams"]) - 4) <= 0.003
        for row in simulation["teams"]:
            assert sum(row["points_distribution"].values()) == 10_000
            assert sum(row["position_distribution"].values()) == 10_000
        reports.append(
            {
                "season": year,
                "status": "passed",
                "official_matches": expected_matches,
                "records": parsed["summary"]["records"],
                "published_table_teams_checked": parsed["validation"]["teams_checked"],
                "simulation_count": simulation["simulation_count"],
                "seed": simulation["seed"],
            }
        )

    calibration = load(ROOT / "data/ratings/calibration.json")
    robustness = load(ROOT / "data/ratings/robustness.json")
    famous = load(ROOT / "data/analytics/famous_matches.json")
    what_if = load(ROOT / "data/analytics/what_if.json")
    assert calibration["grid"][0]["log_loss"] < calibration["coin_flip_log_loss"]
    assert len(robustness["seasons"]) == 19
    assert robustness["comparison_to_elo"]["team_seasons"] == 166
    assert len(famous["matches"]) == 10
    assert len(what_if["seasons"]) == 19
    output = {
        "schema_version": 1,
        "status": "passed",
        "seasons_checked": len(reports),
        "published_table_fields": ["played", "won", "lost", "no_result", "points"],
        "calibration_beats_coin_flip": True,
        "ball_rating_team_seasons": robustness["comparison_to_elo"]["team_seasons"],
        "famous_match_traces": len(famous["matches"]),
        "seasons": reports,
    }
    target = ROOT / "data/validation/index.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Validated {len(reports)} seasons, every distribution, calibration and analysis artifact")


if __name__ == "__main__":
    main()
