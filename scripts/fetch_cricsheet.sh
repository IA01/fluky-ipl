#!/usr/bin/env bash
set -euo pipefail

destination="${1:-data/raw}"
archive="${destination}/ipl_json.zip"

mkdir -p "${destination}"
curl --fail --location --retry 3 \
  'https://cricsheet.org/downloads/ipl_json.zip' \
  --output "${archive}"
unzip -q -o "${archive}" -d "${destination}/ipl_json"
printf 'Cricsheet IPL JSON extracted to %s\n' "${destination}/ipl_json"

