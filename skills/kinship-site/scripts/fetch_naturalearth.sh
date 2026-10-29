#!/bin/zsh
# Downloads the Natural Earth layers used for maps (public domain) into a shared cache, once for all cases.
# Usage: zsh fetch_naturalearth.sh [dir]   (default ~/.cache/kinship-site/naturalearth, ~40 MB)
set -e
DIR=${1:-$HOME/.cache/kinship-site/naturalearth}
mkdir -p "$DIR"
BASE=https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson
for f in ne_10m_ocean ne_10m_lakes ne_10m_rivers_lake_centerlines ne_10m_rivers_europe; do
  [ -s "$DIR/$f.geojson" ] && continue
  curl -fsSL "$BASE/$f.geojson" -o "$DIR/$f.geojson"
  echo "got $f"
done
ls -la "$DIR"
