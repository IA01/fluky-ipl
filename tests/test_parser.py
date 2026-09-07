from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.parse_cricsheet import TeamRegistry, overs_to_balls, season_year, stage_for

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = Path(os.environ.get("IPL_CRICSHEET_ROOT", ROOT / "ipl_json (1)"))
SOURCE_2008 = SOURCE_ROOT / "2008"


class ParserUnitTests(unittest.TestCase):
    def test_inaugural_season_label(self) -> None:
        self.assertEqual(season_year("2007/08"), 2008)
        self.assertEqual(season_year("2009/10"), 2010)
        self.assertEqual(season_year("2020/21"), 2020)

    def test_franchise_aliases(self) -> None:
        registry = TeamRegistry()
        self.assertEqual(registry.resolve("Delhi Daredevils")["id"], "delhi_capitals")
        self.assertEqual(registry.resolve("Kings XI Punjab")["id"], "punjab_kings")
        self.assertNotEqual(registry.resolve("Deccan Chargers")["id"], registry.resolve("Sunrisers Hyderabad")["id"])

    def test_playoff_stage_detection(self) -> None:
        self.assertEqual(stage_for({"event": {"match_number": "1st Semi-Final"}}), "semi_final")
        self.assertEqual(stage_for({"event": {"match_number": "Final"}}), "final")
        self.assertEqual(stage_for({"event": {"match_number": "Elimination Final"}}), "eliminator")
        self.assertEqual(stage_for({"event": {"match_number": "3rd Place Play-Off"}}), "third_place")

    def test_cricket_overs_conversion(self) -> None:
        self.assertEqual(overs_to_balls(20), 120)
        self.assertEqual(overs_to_balls(7.3), 45)


@unittest.skipUnless(SOURCE_2008.exists(), "supplied 2008 Cricsheet archive not available")
class ParserIntegrationTests(unittest.TestCase):
    def test_2008_is_stable_and_complete(self) -> None:
        digests: list[str] = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as directory:
                subprocess.run(
                    [
                        "python3",
                        str(ROOT / "scripts/parse_cricsheet.py"),
                        "--input",
                        str(SOURCE_2008),
                        "--output",
                        directory,
                        "--season",
                        "2008",
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                content = (Path(directory) / "2008.json").read_bytes()
                digests.append(hashlib.sha256(content).hexdigest())
                payload = json.loads(content)
                self.assertEqual(payload["summary"]["matches"], 59)
                self.assertEqual(payload["summary"]["league_matches"], 56)
                self.assertEqual(payload["source"]["files"], 58)
                self.assertEqual(payload["source"]["configured_supplements"], 1)
                self.assertEqual(payload["actual_table"][0]["team"]["abbr"], "RR")
                self.assertEqual(payload["actual_table"][0]["points"], 22)
                self.assertEqual(payload["actual_table"][3]["team"]["abbr"], "DC")
                self.assertEqual(payload["actual_table"][3]["points"], 15)
        self.assertEqual(digests[0], digests[1])


if __name__ == "__main__":
    unittest.main()
