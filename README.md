# How Fluky Was the IPL?

A static analytics feature that asks whether every IPL champion from 2008–2026 was the season’s most repeatable winner. It combines auction-aware Elo, an independent ball-by-ball strength rating, 10,000 fixed-seed season replays, famous-final win probabilities, and a client-side What-If Machine.

Live site: [fluky-ipl.vercel.app](https://fluky-ipl.vercel.app/)

## What is included

- 19 independently validated final points tables
- 190,000 precomputed season simulations
- Match-level Elo with margin of victory and auction-cycle resets
- Ball-level runs-above-par ratings by season, venue, and innings phase
- Momentum, close-game, toss/dew proxy, and regression-to-mean studies
- 10 ball-by-ball final win-probability traces
- 1,000-run deterministic browser simulator for result and strength counterfactuals
- 28 fully static Next.js routes, with no production API or database

## Rebuild the data

Use Python 3.11+ and install the pinned packages in `requirements.txt`. Download/extract the IPL JSON archive with `scripts/fetch_cricsheet.sh`, then pass its directory to the orchestrator:

```bash
python3 scripts/build_all.py --input "/path/to/ipl_json"
```

The stages run in dependency order:

1. Parse and normalise Cricsheet matches.
2. Reconcile every season against the independent published table.
3. Calibrate and build Elo.
4. Run 19 × 10,000 match-level simulations.
5. Build the venue/phase rating, player impact, and famous-match traces.
6. Validate every distribution and write `data/validation/index.json`.

Raw Cricsheet files are intentionally ignored; the fetch script, configuration, and compact derived artifacts are committed.

## Run and verify

```bash
npm install
npm run test:data
npm run validate:data
npm run build
npm run dev
```

Generated JSON contains no wall-clock timestamps. Fixed seeds and stable JSON ordering make successive pipeline runs byte-identical.

## Model in brief

- Base Elo: 1500; new-franchise entry: 1465.
- Mega-auction years 2011, 2014, 2018, 2022, 2025 retain 10% of the prior rating edge; normal seasons retain 40%.
- K, probability scale, and home term are selected on a 2019–2026 retrospective holdout. The current choice is K=24, scale=400, fitted home edge=0.
- Observed no-results remain one point each. Abandoned-without-toss matches never update Elo.
- True counterfactual NRR cannot exist in a match-level simulation, so equal-points ties use wins followed by a sampled symmetric performance-margin proxy.
- Elo is a retrospective season-strength model for replay, not a pre-match forecasting claim.

The site’s Methods page documents formulas, assumptions, lineage, exceptions, calibration, robustness, and limitations in full.

## Data sources

- [Cricsheet IPL downloads](https://cricsheet.org/downloads/)
- [Official IPL match reports](https://www.iplt20.com/)
- Independent published table links are attached to each season artifact and season page.
