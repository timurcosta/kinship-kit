#!/bin/zsh
# Builds the case PDF from pdf-source/report.html with the ex-ussr-kinship-research builder.
# That builder prints the PDF with headless Chrome, which often never exits on macOS: once report.pdf appears
# in its temp folder we copy it and stop only that Chrome.
# Usage: zsh build_pdf.sh <case dir>
set -e
CASE=${1:A}
BUILDER=$HOME/.claude/skills/ex-ussr-kinship-research/scripts/build_pdf.py
OUTNAME=$(python3 -I -c 'import json,sys;print(json.load(open(sys.argv[1]))["pdf"])' "$CASE/pdf-source/web/site.json")
cd "$CASE"
LOG=$(mktemp)
(python3 "$BUILDER" --html pdf-source/report.html --out "$OUTNAME" > "$LOG" 2>&1 &)
for i in $(seq 1 60); do
  sleep 3
  grep -q "PDF собран\|Ошибка" "$LOG" && break
  D=$(ls -d .kinship-pdf-* 2>/dev/null | head -1)
  if [ -n "$D" ] && [ -s "$D/report.pdf" ]; then
    sleep 4
    grep -q "PDF собран" "$LOG" && break
    cp "$D/report.pdf" "$OUTNAME"
    P=$(ps ax -o pid=,args= | grep "$D" | grep -v grep | awk '{print $1}' | head -1)
    [ -n "$P" ] && kill $P
    break
  fi
done
grep "Ошибка" "$LOG" && exit 1
ls -la "$OUTNAME" | awk '{print "PDF:", $5, "bytes,", $6, $7, $8}'
