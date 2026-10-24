#!/usr/bin/env bash
# new_item.sh. create a work_space item from its template, never overwriting.
set -euo pipefail

WS="${AG_WORKSPACE:-$HOME/Documents/work_space}"
MY="$WS/resources_active/_my_active"

die() { echo "error: $*" >&2; exit 1; }

usage() {
  cat <<EOF
new_item.sh <type> <name> [--date YYYYMMDD] [--category DIR] [--dry-run]

Types and destinations (workspace: $WS):
  project         projects_active/<name>
  proposal        proposals_active/<YYYY>_<name>
  presentation    _my_active/my_presentations_active/<YYYY>/<YYYYMMDD>_<name>
  poster          _my_active/my_posters_active/<YYYY>/<YYYYMMDD>_<name>
  conference      _my_active/my_conferences_active/<YYYYMMDD>_<name>
  publication     _my_active/my_publications_active/ongoing/<name>
  review-article  _my_active/my_reviews_active/articles/<name>
  review-call     _my_active/my_reviews_active/projects/<name>
  supervision     _my_active/my_tutoring_active/<category>/<name>   (--category Theses|Stages|postdocs|...)
  training        _my_active/my_training_active/<YYYY>/<YYYYMMDD>_<name>
  application     _my_active/my_applications/<YYYY>_<name>

--date defaults to today. Names: lowercase, underscores, no spaces.
EOF
}

[ $# -ge 2 ] || { usage; exit 1; }
type="$1" name="$2"; shift 2
date="$(date +%Y%m%d)" category="" dry=0
while [ $# -gt 0 ]; do
  case "$1" in
    --date) date="${2:-}"; shift 2 ;;
    --category) category="${2:-}"; shift 2 ;;
    --dry-run) dry=1; shift ;;
    *) die "unknown flag: $1" ;;
  esac
done
[[ "$date" =~ ^[0-9]{8}$ ]] || die "--date must be YYYYMMDD"
[[ "$name" =~ ^[A-Za-z0-9][A-Za-z0-9_.@-]*$ ]] || die "name must be letters, digits, _ . @ - (no spaces)"
year="${date:0:4}"

case "$type" in
  project)        tpl="$WS/projects_active/template_project";                 dest="$WS/projects_active/$name" ;;
  proposal)       tpl="$WS/proposals_active/template_proposal";               dest="$WS/proposals_active/${year}_$name" ;;
  presentation)   tpl="$MY/my_presentations_active/template_presentation";    dest="$MY/my_presentations_active/$year/${date}_$name" ;;
  poster)         tpl="$MY/my_posters_active/template_poster";                dest="$MY/my_posters_active/$year/${date}_$name" ;;
  conference)     tpl="$MY/my_conferences_active/template_conference";        dest="$MY/my_conferences_active/${date}_$name" ;;
  publication)    tpl="$MY/my_publications_active/template_publication";      dest="$MY/my_publications_active/ongoing/$name" ;;
  review-article) tpl="$MY/my_reviews_active/template_review_article";        dest="$MY/my_reviews_active/articles/$name" ;;
  review-call)    tpl="$MY/my_reviews_active/template_review_call";           dest="$MY/my_reviews_active/projects/$name" ;;
  supervision)    [ -n "$category" ] || die "supervision needs --category (e.g. Theses, Stages, postdocs)"
                  tpl="$MY/my_tutoring_active/template_supervision";          dest="$MY/my_tutoring_active/$category/$name" ;;
  training)       tpl="$MY/my_training_active/template_training";             dest="$MY/my_training_active/$year/${date}_$name" ;;
  application)    tpl="$MY/my_applications/template_application";             dest="$MY/my_applications/${year}_$name" ;;
  -h|--help|help) usage; exit 0 ;;
  *) die "unknown type: $type (run with --help)" ;;
esac

[ -d "$tpl" ] || die "template missing: $tpl"
[ -e "$dest" ] && die "already exists: $dest"

if [ "$dry" -eq 1 ]; then
  echo "would copy $tpl -> $dest"
  exit 0
fi

mkdir -p "$(dirname "$dest")"
cp -R "$tpl" "$dest"
find "$dest" -name .DS_Store -delete
rm_md="$dest/read_me.md"
if [ -f "$rm_md" ]; then
  # fill name and date, drop the "copy this folder" instruction
  sed -i.bak -e "s|^- \*\*Name:\*\*.*|- **Name:** $name|" -e "s|^- \*\*Dates:\*\*.*|- **Dates:** created $date|" \
    -e '/^<!-- Copy this folder/d' "$rm_md" && rm -f "$rm_md.bak"
fi
echo "created $dest"
# Projects keep a work journal (_journal/), one template for all: lex-claude/templates/journal.
[ "$type" = project ] && bash "$HOME/.claude/lex-claude/journal.sh" init "$dest"
