#!/bin/zsh
# One-off hosting setup for a case. THE USER RUNS IT in their terminal (it creates cloud resources and keys).
#   1. Yandex Object Storage bucket from site.json → hosting.bucket: public read (no listing), website mode, 200 MB cap.
#   2. Service account <bucket>-deployer with no folder roles, only bucket ACL read+write.
#   3. Its static key goes straight from yc to the GitHub secrets YC_STORAGE_KEY_ID / YC_STORAGE_SECRET (never printed).
#   4. Starts the deploy workflow.
# Needs: yc (logged in), gh (gh auth login), the private repo from site.json → hosting.repo with the case pushed.
# Usage: zsh setup_hosting.sh <case dir>
set -e
YC=${YC:-$HOME/yandex-cloud/bin/yc}
GH=${GH:-gh}
CASE=${1:A}
read BUCKET REPO <<< "$(python3 -I -c 'import json,sys;h=json.load(open(sys.argv[1]))["hosting"];print(h["bucket"],h["repo"])' "$CASE/pdf-source/web/site.json")"
SA_NAME=${BUCKET:0:50}-deployer
SA_NAME=${SA_NAME:l}

"$GH" repo view "$REPO" >/dev/null 2>&1 || { echo "repo $REPO not found: create it first (gh repo create $REPO --private --source $CASE --remote origin --push)"; exit 1; }

if ! "$YC" storage bucket get "$BUCKET" >/dev/null 2>&1; then
  "$YC" storage bucket create --name "$BUCKET" --public-read --max-size 209715200 >/dev/null
  echo "bucket created: $BUCKET"
fi
"$YC" storage bucket update --name "$BUCKET" --website-settings '{"index":"index.html","error":"index.html"}' >/dev/null
echo "website mode on"

SA=$("$YC" iam service-account get --name "$SA_NAME" --format json 2>/dev/null | python3 -I -c 'import json,sys;print(json.load(sys.stdin)["id"])' || true)
if [ -z "$SA" ]; then
  SA=$("$YC" iam service-account create --name "$SA_NAME" --description "GitHub Actions: deploy only to bucket $BUCKET" --format json \
        | python3 -I -c 'import json,sys;print(json.load(sys.stdin)["id"])')
fi
echo "service account: $SA_NAME ($SA), no folder roles"

# NB: --grants replaces the bucket ACL; public read for the site is a separate flag and is not affected
"$YC" storage bucket update --name "$BUCKET" \
  --grants grant-type=grant-type-account,grantee-id=$SA,permission=permission-read \
  --grants grant-type=grant-type-account,grantee-id=$SA,permission=permission-write >/dev/null
echo "bucket ACL: read+write for $SA_NAME on $BUCKET only"

"$YC" iam access-key create --service-account-id $SA --description "github actions $REPO" --format json \
  | python3 -I -c '
import json, subprocess, sys
k = json.load(sys.stdin)
for name, val in (("YC_STORAGE_KEY_ID", k["access_key"]["key_id"]), ("YC_STORAGE_SECRET", k["secret"])):
    subprocess.run([sys.argv[1], "secret", "set", name, "-R", sys.argv[2]], input=val.encode(), check=True)
' "$GH" "$REPO"
echo "GitHub secrets set: YC_STORAGE_KEY_ID, YC_STORAGE_SECRET"

"$GH" workflow run deploy.yml -R "$REPO"
echo "deploy started: https://github.com/$REPO/actions"
echo "site: https://$BUCKET.website.yandexcloud.net/"
