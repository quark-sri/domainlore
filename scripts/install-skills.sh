#!/usr/bin/env bash
# Install the domainlore skills for AI coding agents that read SKILL.md.
#
# Usage:
#   scripts/install-skills.sh --agent <name>|all (--user | --project <repo>) [--copy]
#
# The skill folders come from the official documentation of each agent
# (the same table as qestack's scripts/install-skills.sh, checked 2026-10-27).
# Works with bash 3.2 (macOS) and later.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
SKILLS="$HERE/skills"
AGENTS="claude codex cursor copilot gemini antigravity devin opencode cline"
# A copied skill gets this file, so that a later install knows it may replace the folder.
MARKER=".domainlore-skill"

usage() {
  cat <<EOF
Install the domainlore skills for an AI coding agent.

Usage:
  $0 --agent <name>|all (--user | --project <repo>) [--copy]

Options:
  --agent <name>    one of: $AGENTS, or all
                    (all: every agent except claude; Claude Code gets the skills from the domainlore plugin)
  --user            install for your user (all projects)
  --project <repo>  install into one repository
  --copy            copy the skills (default: symbolic links to skills/ of this clone; on Windows, use --copy)
  -h, --help        show this help

Skill folders:
  agent        project              user
  claude       .claude/skills       ~/.claude/skills
  codex        .agents/skills       ~/.agents/skills
  cursor       .agents/skills       ~/.agents/skills
  copilot      .agents/skills       ~/.agents/skills
  gemini       .agents/skills       ~/.agents/skills
  antigravity  .agents/skills       ~/.gemini/antigravity-cli/skills and ~/.gemini/config/skills
  devin        .agents/skills       ~/.agents/skills
  opencode     .agents/skills       ~/.agents/skills
  cline        .cline/skills        ~/.cline/skills

Links point to skills/ of this clone, so git pull updates them. Copies do not change:
after git pull, run the same command again.

The skills run the lore command. Install it once (docx and pdf: read Word and PDF documents):
  uv tool install "domainlore[docx,pdf] @ git+https://github.com/quark-sri/domainlore"
EOF
}

# The skill folders of one agent, one for each line. $1: agent, $2: user or project.
folders() {
  case "$1:$2" in
    claude:user) echo "$HOME/.claude/skills" ;;
    claude:project) echo ".claude/skills" ;;
    cline:user) echo "$HOME/.cline/skills" ;;
    cline:project) echo ".cline/skills" ;;
    antigravity:user) echo "$HOME/.gemini/antigravity-cli/skills"; echo "$HOME/.gemini/config/skills" ;;
    *:user) echo "$HOME/.agents/skills" ;;
    *:project) echo ".agents/skills" ;;
  esac
}

# True if $1 is a skill folder or link that this script installed (or a broken link).
ours() {
  local dst="$1" to
  if [ -L "$dst" ]; then
    to="$(readlink "$dst")"
    case "$to" in "$SKILLS"/*) return 0 ;; esac
    [ -e "$dst" ] || return 0  # a broken link holds nothing
    return 1
  fi
  [ ! -e "$dst" ] || [ -f "$dst/$MARKER" ]
}

# Install the skills into $1. $2: link or copy. A folder or link that is not ours is skipped.
SKIPPED=0
install_into() {
  local target="$1" mode="$2" n=0 d name dst
  mkdir -p "$target"
  for d in "$SKILLS"/*/; do
    [ -f "$d/SKILL.md" ] || continue
    name="$(basename "$d")"
    dst="$target/$name"
    if ! ours "$dst"; then
      echo "skip $name: $dst exists and is not a domainlore skill"
      SKIPPED=$((SKIPPED + 1))
      continue
    fi
    rm -rf "$dst"
    if [ "$mode" = copy ]; then
      cp -R "${d%/}" "$dst"
      echo "Installed by domainlore scripts/install-skills.sh. Run it again to update this skill." > "$dst/$MARKER"
    else
      ln -s "${d%/}" "$dst"
    fi
    n=$((n + 1))
  done
  echo "$target: $n skills (${mode})"
}

AGENT="" SCOPE="" PROJECT="" MODE=link
while [ $# -gt 0 ]; do
  case "$1" in
    --agent) AGENT="${2:-}"; shift 2 || { usage >&2; exit 2; } ;;
    --user) SCOPE=user; shift ;;
    --project) SCOPE=project; PROJECT="${2:-}"; shift 2 || { usage >&2; exit 2; } ;;
    --copy) MODE=copy; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

LIST=""
[ "$AGENT" = all ] && LIST="${AGENTS#claude }"
for a in $AGENTS; do
  [ "$a" = "$AGENT" ] && LIST="$a"
done
if [ -z "$LIST" ]; then
  echo "unknown agent: '${AGENT}'. Use one of: $AGENTS, or all" >&2
  exit 2
fi
if [ -z "$SCOPE" ] || { [ "$SCOPE" = project ] && [ ! -d "$PROJECT" ]; }; then
  echo "give --user, or --project with an existing repository folder" >&2
  exit 2
fi

DONE=""
for a in $LIST; do
  while IFS= read -r f; do
    [ "$SCOPE" = project ] && f="$(cd "$PROJECT" && pwd)/$f"
    case " $DONE " in *" $f "*) continue ;; esac  # agents that share one folder get one install
    DONE="$DONE $f"
    install_into "$f" "$MODE"
  done <<EOF
$(folders "$a" "$SCOPE")
EOF
done

case " $LIST " in *" claude "*)
  echo "Note: if the domainlore Claude Code plugin is also installed, Claude Code shows each skill two times." ;;
esac
if ! command -v lore >/dev/null 2>&1; then
  echo "The skills run the lore command, and it is not on your PATH. Install it:"
  echo "  uv tool install \"domainlore[docx,pdf] @ git+https://github.com/quark-sri/domainlore\""
fi
if [ "$SKIPPED" -gt 0 ]; then
  echo "$SKIPPED skill folders were skipped. The skills link to each other, so some links do not work." >&2
  echo "Move or rename the skipped folders, then run the same command again." >&2
  exit 1
fi
