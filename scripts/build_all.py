#!/usr/bin/env python3
"""Run the complete deterministic offline data pipeline in dependency order."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*arguments: str) -> None:
    subprocess.run([sys.executable, *arguments], cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Extracted Cricsheet IPL JSON root")
    args = parser.parse_args()
    raw = str(args.input.expanduser().resolve())
    run("scripts/parse_cricsheet.py", "--input", raw, "--output", "data/parsed/seasons")
    run("scripts/build_model.py")
    run("scripts/build_ball_ratings.py", "--input", raw)
    run("scripts/validate_outputs.py")


if __name__ == "__main__":
    main()
