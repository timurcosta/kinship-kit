#!/bin/zsh
# Manual publish of the case site to its Yandex Object Storage bucket, without GitHub (the same thing CI does on push).
# Usage: zsh publish_manual.sh <case dir>     (bucket: site.json → hosting.bucket; uses the user's yc profile)
set -e
YC=${YC:-$HOME/yandex-cloud/bin/yc}
CASE=${1:A}
BUCKET=$(python3 -I -c 'import json,sys;print(json.load(open(sys.argv[1]))["hosting"]["bucket"])' "$CASE/pdf-source/web/site.json")
STAGE=$(mktemp -d)/site
python3 -I "$HOME/.claude/skills/kinship-site/scripts/stage_public.py" "$CASE" "$STAGE"
cd "$STAGE"
# yc guesses text/plain for js/css/svg, so those go one by one with an explicit type
"$YC" storage s3 cp --recursive --only-show-errors --exclude "*.js" --exclude "*.css" --exclude "*.svg" ./ "s3://$BUCKET/"
for spec in "js:application/javascript; charset=utf-8" "css:text/css; charset=utf-8" "svg:image/svg+xml; charset=utf-8"; do
  ext=${spec%%:*}; ct=${spec#*:}
  find . -type f -name "*.$ext" | sed 's#^\./##' | while read f; do
    "$YC" storage s3 cp --only-show-errors --content-type "$ct" "$f" "s3://$BUCKET/$f"
  done
done
rm -rf "${STAGE:h}"
echo "https://$BUCKET.website.yandexcloud.net/"
