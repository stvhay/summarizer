#!/usr/bin/env bash
# Read-only structural check. Does not prove full decode or subtitle fidelity.
set -euo pipefail
if [[ $# -lt 1 || $# -gt 2 || (${2:-} != '' && ${2:-} != --no-subtitles) ]]; then
    echo 'Usage: bash scripts/verify-archive.sh ARCHIVE [--no-subtitles]' >&2
    exit 2
fi
archive=$1
[[ -s "$archive" ]] || { echo "Missing or empty archive: $archive" >&2; exit 1; }
format=$(ffprobe -v error -show_entries format=format_name -of default=nw=1:nk=1 "$archive")
[[ ",$format," == *,matroska,* ]] || { echo 'Archive must be Matroska' >&2; exit 1; }
streams=$(ffprobe -v error -show_entries stream=codec_type -of csv=p=0 "$archive")
required='video audio subtitle'
[[ ${2:-} != --no-subtitles ]] || required='video audio'
for kind in $required; do
    grep -qx "$kind" <<< "$streams" || { echo "Archive missing $kind stream" >&2; exit 1; }
done
printf 'PASS: archive structure (%s): %s\n' "$required" "$archive"
