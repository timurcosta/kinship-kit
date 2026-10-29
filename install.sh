#!/bin/zsh
# Ставит навыки в ~/.claude/skills и кладёт CLAUDE.md в папку с делами.
# Запуск: zsh install.sh ~/genealogy
set -e
HERE=${0:A:h}
TARGET=${1:-$HOME/genealogy}
SKILLS=$HOME/.claude/skills

mkdir -p "$SKILLS" "$TARGET"

# Исследование: чужой навык, ставим из репозитория автора
if [[ -d $SKILLS/ex-ussr-kinship-research/.git ]]; then
  git -C "$SKILLS/ex-ussr-kinship-research" pull --ff-only
else
  git clone https://github.com/DenisSergeevitch/ex-ussr-kinship-research "$SKILLS/ex-ussr-kinship-research"
fi

# Сайт из отчёта
rsync -a "$HERE/skills/kinship-site/" "$SKILLS/kinship-site/"

# Правила для Claude: свой CLAUDE.md не затираем
if [[ -e $TARGET/CLAUDE.md ]]; then
  cp "$HERE/CLAUDE.md" "$TARGET/CLAUDE.from-timur.md"
  echo "В $TARGET уже есть CLAUDE.md — новый положен рядом как CLAUDE.from-timur.md, объедини их."
else
  cp "$HERE/CLAUDE.md" "$TARGET/CLAUDE.md"
fi

echo "Готово. Открой Claude Code в $TARGET."
