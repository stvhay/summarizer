#!/usr/bin/env bash
# Offline regression checks; requires Bash, yt-dlp, ffmpeg, and ffprobe.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -f scripts/archive.conf || ! -f scripts/verify-archive.sh ]]; then
    echo 'FAIL: archive selection policy and verification gate must exist' >&2
    exit 1
fi
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

select_format() {
    local expected=$1 actual
    printf '{"id":"offline","title":"Offline fixture","extractor":"generic","webpage_url":"https://example.invalid/video","formats":%s}\n' "$(</dev/stdin)" > "$work/formats.json"
    actual=$(yt-dlp --ignore-config --config-locations scripts/archive.conf \
        --load-info-json "$work/formats.json" --simulate --print format_id)
    [[ "$actual" == "$expected" ]] || {
        echo "FAIL: expected format $expected, got $actual" >&2
        exit 1
    }
}

# Resolution outranks codec; audio remains a separate stream.
select_format 'h264-1080+audio-opus' <<'JSON'
[
 {"format_id":"av1-720","url":"https://example.invalid/av1","ext":"mp4","vcodec":"av01","acodec":"none","height":720,"width":1280,"fps":30,"tbr":3000},
 {"format_id":"h264-1080","url":"https://example.invalid/h264","ext":"mp4","vcodec":"avc1","acodec":"none","height":1080,"width":1920,"fps":30,"tbr":6000},
 {"format_id":"audio-opus","url":"https://example.invalid/audio","ext":"webm","vcodec":"none","acodec":"opus","abr":128}
]
JSON

# Bitrate outranks codec at equal resolution/frame rate.
select_format 'h264-high+audio-opus' <<'JSON'
[
 {"format_id":"av1-low","url":"https://example.invalid/av1","ext":"mp4","vcodec":"av01","acodec":"none","height":1080,"width":1920,"fps":30,"tbr":2000},
 {"format_id":"h264-high","url":"https://example.invalid/h264","ext":"mp4","vcodec":"avc1","acodec":"none","height":1080,"width":1920,"fps":30,"tbr":6000},
 {"format_id":"audio-opus","url":"https://example.invalid/audio","ext":"webm","vcodec":"none","acodec":"opus","abr":128}
]
JSON

# Open codecs win ties, including the audio choice.
select_format 'av1+audio-opus' <<'JSON'
[
 {"format_id":"h264","url":"https://example.invalid/h264","ext":"mp4","vcodec":"avc1","acodec":"none","height":1080,"width":1920,"fps":30,"tbr":3000},
 {"format_id":"vp9","url":"https://example.invalid/vp9","ext":"webm","vcodec":"vp9","acodec":"none","height":1080,"width":1920,"fps":30,"tbr":3000},
 {"format_id":"av1","url":"https://example.invalid/av1","ext":"mp4","vcodec":"av01","acodec":"none","height":1080,"width":1920,"fps":30,"tbr":3000},
 {"format_id":"aac","url":"https://example.invalid/aac","ext":"m4a","vcodec":"none","acodec":"mp4a.40.2","abr":128},
 {"format_id":"audio-opus","url":"https://example.invalid/opus","ext":"webm","vcodec":"none","acodec":"opus","abr":128}
]
JSON

# Hosts offering only a combined stream still work.
select_format 'combined' <<'JSON'
[
 {"format_id":"combined","url":"https://example.invalid/video","ext":"mp4","vcodec":"avc1","acodec":"mp4a.40.2","height":1080,"width":1920,"tbr":3000}
]
JSON

ffmpeg -v error -nostdin -f lavfi -i 'color=size=32x32:rate=5' \
    -f lavfi -i 'sine=frequency=440:sample_rate=8000' -t 0.4 \
    -c:v ffv1 -c:a pcm_s16le "$work/av.mkv"
printf '1\n00:00:00,000 --> 00:00:00,400\nTest subtitle\n' > "$work/subtitle.srt"
ffmpeg -v error -nostdin -i "$work/av.mkv" -i "$work/subtitle.srt" \
    -map 0 -map 1 -c copy "$work/with subs.mkv"
ffmpeg -v error -nostdin -i "$work/av.mkv" -map 0:v -c copy "$work/video.mkv"
ffmpeg -v error -nostdin -i "$work/av.mkv" -map 0:a -c copy "$work/audio.mkv"
ffmpeg -v error -nostdin -i "$work/av.mkv" -c copy -f nut "$work/not-matroska.mkv"
printf 'not media\n' > "$work/broken.mkv"

# Exercise the real download/remux path without network access.
ffmpeg -v error -nostdin -i "$work/av.mkv" -c:v mpeg4 -c:a aac "$work/source.mp4"
printf '{"id":"local","title":"Local fixture","extractor":"generic","webpage_url":"https://example.invalid/video","formats":[{"format_id":"combined","url":"file:%s/source.mp4","ext":"mp4","vcodec":"mpeg4","acodec":"aac"}]}\n' "$work" > "$work/local.json"
yt-dlp --ignore-config --config-locations scripts/archive.conf --enable-file-urls \
    --load-info-json "$work/local.json" -o "$work/download.%(ext)s" --quiet
bash scripts/verify-archive.sh "$work/download.mkv" --no-subtitles
[[ -s "$work/source.mp4" ]]

reject() {
    if bash scripts/verify-archive.sh "$@" > "$work/rejection.log" 2>&1; then
        echo "FAIL: archive check accepted $*" >&2
        exit 1
    fi
}
bash scripts/verify-archive.sh "$work/with subs.mkv"
bash scripts/verify-archive.sh "$work/av.mkv" --no-subtitles
reject "$work/av.mkv"
reject "$work/video.mkv" --no-subtitles
reject "$work/audio.mkv" --no-subtitles
reject "$work/not-matroska.mkv" --no-subtitles
reject "$work/broken.mkv"
reject "$work/missing.mkv"
reject "$work/with subs.mkv" --typo
reject
printf 'PASS: offline format selection and archive verification\n'
