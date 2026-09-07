from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

from scripts.build_model import margin_multiplier, probability, runs_test

ROOT = Path(__file__).resolve().parents[1]


class EloUnitTests(unittest.TestCase):
    def test_probability_is_symmetric(self) -> None:
        self.assertAlmostEqual(probability(1500, 1500, 400), 0.5)
        self.assertAlmostEqual(probability(1600, 1500, 400) + probability(1500, 1600, 400), 1)
        self.assertGreater(probability(1500, 1500, 400, 40), 0.5)

    def test_margin_multiplier_is_bounded(self) -> None:
        run_match = {"outcome": {"type": "win", "margin": {"unit": "runs", "value": 50}}}
        wicket_match = {
            "outcome": {"type": "win", "margin": {"unit": "wickets", "value": 10}},
            "innings": [{}, {"legal_balls": 60}], "scheduled_overs": 20, "balls_per_over": 6,
        }
        self.assertAlmostEqual(margin_multiplier(run_match), 2.0)
        self.assertLessEqual(margin_multiplier(wicket_match), 2.25)
        self.assertGreater(margin_multiplier(wicket_match), 1)

    def test_runs_test_flags_clustering(self) -> None:
        clustered = runs_test([1] * 8 + [0] * 8)
        self.assertIsNotNone(clustered)
        self.assertLess(clustered["z_score"], -1.96)


class BakedOutputTests(unittest.TestCase):
    def test_selected_calibration_beats_coin_flip(self) -> None:
        calibration = json.loads((ROOT / "data/ratings/calibration.json").read_text())
        self.assertLess(calibration["grid"][0]["log_loss"], math.log(2))

    def test_every_simulation_distribution_sums_to_seeded_count(self) -> None:
        for year in range(2008, 2027):
            simulation = json.loads((ROOT / f"data/simulations/{year}.json").read_text())
            for team in simulation["teams"]:
                self.assertEqual(sum(team["points_distribution"].values()), 10_000)
                self.assertEqual(sum(team["position_distribution"].values()), 10_000)


if __name__ == "__main__":
    unittest.main()
