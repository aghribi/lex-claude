#!/usr/bin/env bash
# Vendor third-party skills into skills/ at pinned commits, then apply local patches.
# Re-run after bumping a commit below. Sources, licenses and patches: THIRD_PARTY.md.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# repo commit skills...
SOURCES=(
  "K-Dense-AI/scientific-agent-skills a1043ef544e3a100c28e70a736b6cf32554d0677 skills
    scientific-critical-thinking hypothesis-generation scientific-brainstorming experimental-design
    statistical-analysis uncertainty-and-units literature-review citation-management paper-lookup
    scientific-writing peer-review scientific-visualization
    stable-baselines3 pufferlib pymoo pytorch-lightning scikit-learn shap pymc"
  "flonat/flonat-research da276000406995dcef886efc72ad7dd9665eedfd skills
    devils-advocate numerical-check verify-math computational-experiments review-response proofread"
  "obra/superpowers bb92a77741419a4ab5f06e711a283343f1ada0c3 skills
    systematic-debugging verification-before-completion"
)

fetch() {
  local repo="$1" commit="$2" dir="$TMP/${1//\//_}"
  git init -q "$dir"
  git -C "$dir" fetch -q --depth 1 "https://github.com/$repo.git" "$commit"
  git -C "$dir" checkout -q FETCH_HEAD
  echo "$dir"
}

for entry in "${SOURCES[@]}"; do
  read -r repo commit subdir skills <<<"$(echo $entry)"
  src="$(fetch "$repo" "$commit")"
  mkdir -p "$ROOT/licenses"
  cp "$(ls "$src"/LICENSE* | head -1)" "$ROOT/licenses/${repo//\//_}.txt"
  for skill in $skills; do
    rm -rf "$ROOT/skills/$skill"
    cp -R "$src/$subdir/$skill" "$ROOT/skills/$skill"
    echo "vendored $repo $skill"
  done
done

# Patch K-Dense: drop the "Citing Scientific Agent Skills" section, which tells the
# agent to add K-Dense's paper to the user's manuscripts.
for f in "$ROOT"/skills/*/SKILL.md; do
  grep -q '^## Citing Scientific Agent Skills' "$f" || continue
  awk '/^## Citing Scientific Agent Skills/{skip=1; next} skip && /^## /{skip=0} !skip' "$f" >"$f.tmp"
  mv "$f.tmp" "$f"
done

# Patch obra: point at the vendored skill names, not the superpowers plugin.
sed -i.bak \
  -e 's/Use the `superpowers:test-driven-development` skill for writing proper failing tests/Write a failing test that reproduces the bug/' \
  -e 's/`superpowers:verification-before-completion`/`verification-before-completion`/' \
  "$ROOT/skills/systematic-debugging/SKILL.md"
rm -f "$ROOT/skills/systematic-debugging/SKILL.md.bak"

if grep -rlE 'superpowers:|^## Citing Scientific Agent Skills' "$ROOT/skills"; then
  echo "error: unpatched upstream text left in the files above" >&2
  exit 1
fi
echo "done."
