#!/usr/bin/env bash
# Download Census TIGER/Line 2024 tract and block-group shapefiles for Florida.
# Idempotent: skips anything already on disk.
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)/boundaries"
mkdir -p "$DIR"
for f in TRACT/tl_2024_12_tract BG/tl_2024_12_bg; do
  b=$(basename "$f")
  if [ ! -f "$DIR/$b.zip" ]; then
    echo "downloading $b.zip"
    curl -sS -o "$DIR/$b.zip" "https://www2.census.gov/geo/tiger/TIGER2024/$f.zip"
  else
    echo "$b.zip already present"
  fi
done
