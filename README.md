# How Fluky Was the IPL?

A static, reproducible analytics project that separates IPL skill from season-level luck. Cricsheet ball-by-ball files are parsed offline; later pipeline stages will build Elo ratings and replay each season 10,000 times. The Next.js site only reads baked JSON.

## First milestone

- Static Next.js 14 + TypeScript + Tailwind shell
- Deterministic Cricsheet JSON ingest
- Explicit season and franchise identity configuration
- Parsed 2008 season artifact with the actual league table
- Raw source files excluded from Git

## Run locally

```bash
npm install
python3 scripts/parse_cricsheet.py \
  --input "ipl_json (1)" \
  --output data/parsed/seasons \
  --season 2008
npm run dev
```

The parser accepts either the extracted Cricsheet root or a specific season directory. Download fresh data with `./scripts/fetch_cricsheet.sh`.

## Reproducibility

```bash
npm run test:data
npm run build
```

`test:data` parses 2008 twice and compares the SHA-256 digests. Generated JSON contains no wall-clock timestamps and is written with stable ordering.

## Data policy

Cricsheet data is free to download from [cricsheet.org](https://cricsheet.org/downloads/). This repository commits the fetch/parser code and compact derived artifacts, not the raw ball-by-ball archive.

