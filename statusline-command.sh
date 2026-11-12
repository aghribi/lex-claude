#!/usr/bin/env bash
# Managed by lex-claude. Source: $INSTALL_DIR/statusline-command.sh
# Renders: ➜ dir git:(branch) ✗ identity lang:xx tok:Nk genN ←predecessor

set -u
input=$(cat)

j() { jq -r "$1" 2>/dev/null <<<"$input"; }
cwd=$(j '.workspace.current_dir // empty')
[ -z "$cwd" ] && cwd=$(j '.cwd // empty')
dir_name=$(basename "${cwd:-?}")

git_info=""
if [ -n "$cwd" ] && git -C "$cwd" rev-parse --git-dir >/dev/null 2>&1; then
    branch=$(git -C "$cwd" --no-optional-locks symbolic-ref --short HEAD 2>/dev/null \
             || git -C "$cwd" --no-optional-locks rev-parse --short HEAD 2>/dev/null)
    if [ -n "$branch" ]; then
        if git -C "$cwd" --no-optional-locks diff --quiet 2>/dev/null \
           && git -C "$cwd" --no-optional-locks diff --cached --quiet 2>/dev/null; then
            git_info=$(printf " \033[1;34mgit:(\033[0;31m%s\033[1;34m)\033[0m" "$branch")
        else
            git_info=$(printf " \033[1;34mgit:(\033[0;31m%s\033[1;34m) \033[0;33m✗\033[0m" "$branch")
        fi
    fi
fi

ident_info=""
if [ -L "$HOME/.claude/CLAUDE.md" ]; then
    ident=$(basename "$(readlink "$HOME/.claude/CLAUDE.md")" .md)
    [ -n "$ident" ] && ident_info=$(printf " \033[0;35m%s\033[0m" "$ident")
fi

lang_info=""
LEX_LANG_FILE="$HOME/.claude/lex-claude/.lang"
if [ -f "$LEX_LANG_FILE" ]; then
    lang=$(tr -d '[:space:]' < "$LEX_LANG_FILE" 2>/dev/null)
    [ -n "$lang" ] && lang_info=$(printf " \033[2;35m%s\033[0m" "$lang")
fi

model_info=""
LEX_MODEL_FILE="$HOME/.claude/lex-claude/.model"
if [ -f "$LEX_MODEL_FILE" ]; then
    model=$(tr -d '[:space:]' < "$LEX_MODEL_FILE" 2>/dev/null)
    if [ -n "$model" ]; then
        model="${model#claude-}"
        model=$(echo "$model" | sed 's/-[0-9]\{8\}//; s/\([0-9]\)-\([0-9]\)/\1.\2/')
        model_info=$(printf " \033[0;33m%s\033[0m" "$model")
    fi
fi

tok_info=""
ctx_tokens=$(j '.context_window.used_tokens // empty')
if [ -z "$ctx_tokens" ]; then
    ctx_used=$(j '.context_window.used_percentage // empty')
    if [ -n "$ctx_used" ]; then
        total=$(j '.context_window.total_tokens // .context_window.window_size // 1000000')
        ctx_tokens=$(awk -v u="$ctx_used" -v t="$total" 'BEGIN{printf "%d", u*t/100}')
    fi
fi
if [ -n "$ctx_tokens" ]; then
    threshold=${LEX_CLAUDE_DUMB_ZONE_TOKENS:-300000}
    k=$(awk -v t="$ctx_tokens" 'BEGIN{printf "%d", t/1000}')
    if [ "$ctx_tokens" -ge "$threshold" ] 2>/dev/null; then
        tok_info=$(printf " \033[1;31mtok:%dk\033[0m" "$k")
    else
        tok_info=$(printf " \033[2;37mtok:%dk\033[0m" "$k")
    fi
fi

# Succession lineage, written by succeed.sh on handover and by `ag lineage link`:
# "gen<TAB>predecessor-id[<TAB>link]".
lineage_info=""
session_id=$(j '.session_id // empty')
LEX_LINEAGE_FILE="$HOME/.claude/lex-claude/state/lineage/${session_id//[^A-Za-z0-9-]/}"
if [ -n "$session_id" ] && [ -f "$LEX_LINEAGE_FILE" ]; then
    IFS=$'\t' read -r gen parent _ < "$LEX_LINEAGE_FILE"
    [ -n "${gen:-}" ] && [ -n "${parent:-}" ] && lineage_info=$(printf " \033[2;36mgen%s ←%s\033[0m" "$gen" "$(printf '%s' "${parent:0:8}" | tr 'A-Z' 'a-z')")
fi

printf "\033[1;32m➜\033[0m  \033[0;36m%s\033[0m%s%s%s%s%s%s" \
    "$dir_name" "$git_info" "$ident_info" "$model_info" "$lang_info" "$tok_info" "$lineage_info"
