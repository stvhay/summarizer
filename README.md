# Video Summarizer

Turn any video into a structured markdown summary thorough enough to replace watching it.

This is an agent-driven workflow for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) or Pi, not a standalone application. `CLAUDE.md` defines the canonical workflow; media tools handle downloads, transcription, and frame extraction. A shared yt-dlp config and a small archive verifier make the mechanical steps repeatable.

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) or Pi
- [direnv](https://direnv.net/) (hooks into your shell to auto-load the environment)

Plus one of:
- [Nix](https://nixos.org/download/) with flakes enabled, **or**
- [Homebrew](https://brew.sh/) (macOS)

## Setup (Nix)

```bash
git clone https://github.com/stvhay/summarizer.git
cd summarizer
direnv allow    # loads tools from flake.nix, including whisper-cpp
```

## Setup (Homebrew)

Install the dependencies:

```bash
brew install uv node yt-dlp ffmpeg imagemagick mkvtoolnix python
```

Then clone and allow direnv:

```bash
git clone https://github.com/stvhay/summarizer.git
cd summarizer
direnv allow    # creates working directories; verifies dependencies are present
```

If core tools are missing, direnv reports them. Nix and Homebrew package lists are maintained separately; they need not be identical.

Optional capabilities are checked when needed:

- **Local transcription:** `whisper-cli` and `local/models/ggml-large-v3-turbo.bin`. On Homebrew, install with `brew install whisper-cpp`; see `CLAUDE.md` for the model source. Nix already includes Whisper.
- **Gist publishing:** authenticated `gh` CLI (`brew install gh` on Homebrew).

Missing optional tools block only the relevant step. Preserve partial work rather than claiming a complete summary.

## Start

```bash
claude    # or: pi
```

## Usage

Paste a video URL; the agent follows `CLAUDE.md`. For local video material without a named path, place it in `local/inbox/`.

1. Identifies the source and acquires one quality-first `.mkv` archive
2. Obtains subtitles or transcribes the archive locally
3. Preserves metadata, transcript, and source/ASR subtitles; embeds subtitles
4. Writes a genre-aware summary: claim-led for interviews/news, dependency-led for academic/technical talks
5. Verifies technical claims against primary sources and extracts informative visuals from the same archive
6. Applies a final copy-editing pass
7. Verifies archive, summary, and provenance before removing explicit disposable files
8. Optionally publishes the summary to GitHub Gist

Works with YouTube, archive.org, and any other site [yt-dlp supports](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

## Mechanical preparation helper

Requires Python **3.11+**, ffmpeg, ffprobe, and Bash; online sources also need **uv and Node.js**. Python, uv and Node.js are explicit in the Nix shell and Homebrew setup. After changing `flake.nix`, restart the session so direnv reloads it.

Online metadata, archives and subtitles use `scripts/yt-dlp.sh`. This launcher refreshes the [latest official GitHub nightly](https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/latest) through uv on each invocation, with yt-dlp's default Python dependencies. It runs in an isolated environment and ignores Python import paths that could load an older Nix package. It does not update global packages or the Nix store. Resolution/install failures stop preparation; there is no fallback to the installed yt-dlp. GitHub and dependency-index access are required. Nightlies can regress; this is deliberately not a pinned runtime.

Use the same launcher for manual online commands:

```bash
bash scripts/yt-dlp.sh --version
bash scripts/yt-dlp.sh --ignore-config -F 'https://www.youtube.com/watch?v=VIDEO_ID'
```

Local preparation, capture, verification and completed resume do not refresh yt-dlp. The packaged `yt-dlp` remains available for offline regression checks. The launcher explicitly enables Node.js (`--js-runtimes node`) for YouTube challenges; the Python package does not install Node. Nix and Homebrew setup provide it.

From the repository root:

```bash
python3 scripts/media-prep.py prepare 'https://www.youtube.com/watch?v=VIDEO_ID' \
  --slug four-to-six-title-words
python3 scripts/media-prep.py prepare '/absolute/path/recording.mp4' \
  --slug four-to-six-title-words --subtitles '/absolute/path/captions.srt'
python3 scripts/media-prep.py capture local/summaries/four-to-six-title-words
python3 scripts/media-prep.py capture local/summaries/four-to-six-title-words --at 120 245.5
python3 scripts/media-prep.py verify local/summaries/four-to-six-title-words
```

- `prepare` acquires one archive using the shared policy, selects source subtitles before ASR, preserves provenance, writes a timestamped transcript, and verifies subtitle embedding. It does **not** write a summary.
- Supply a 4–6-word lowercase title slug. Online IDs come from yt-dlp; local IDs default to a content-hash prefix (`--id` overrides). Local metadata options: `--title`, `--speaker`, `--date`, `--source-url`; unknown speaker/date/URL remain null.
- `--subtitles` accepts SRT, VTT, or JSON3. Embedded text tracks are selected by `--language` (default `en`), or use `--subtitle-stream INDEX` for an ambiguous/nonmatching track. VTT uses ffmpeg's parser; JSON3 uses source event timing without deduplicating rolling captions. Inspect the full transcript.
- When no source subtitles exist, ASR requires `whisper-cli` and `--model` (default `local/models/ggml-large-v3-turbo.bin`). Missing prerequisites preserve the archive and metadata. For archive.org, first check the item's download page and pass a downloaded sidecar; use `--source-subtitles-checked` only after finding none usable.
- `capture` returns 12 overview frames by default, or five-frame bursts at each requested time in seconds. Candidates stay in `local/transcripts/<id>.prep/`; visual judgment, image selection and optimization remain agent-owned. Bursts too near the end fail and retain partial frames.
- `verify` is read-only: it checks artifact hashes, provenance copies, archive structure, embedded cue text/timing and retained pre-subtitle media. It does not certify ASR accuracy, full playback, summary claims, links or human review.

Commands return compact JSON with artifact/log paths and warnings; runtime failures return `status: blocked` and exit 1. Invalid CLI usage prints argparse help/errors and exits 2. `--workspace` changes the artifact root (default `local`). Paths must not traverse symlinks; use their real paths. Logs, metadata and manifests are private local artifacts and may contain signed URLs. Do not publish them.

### Preservation and resumption

The helper creates a source-owned `.media-prep.json` in the summary directory and reserves `local/transcripts/<id>.prep/`. It refuses existing unowned directories, conflicting IDs, changed recorded artifacts, symlink paths and concurrent work. It does not adopt older manually prepared summaries.

Rerun the same `prepare` command to resume verified stages. Before subtitle selection completes, you may supply a newly found sidecar or missing model. After selection, a different subtitle input is a conflict. After ordinary downloader failures, the manifest records pending output hashes separately from completed artifacts. Unchanged partial/component files can resume; missing, changed, unrecorded or symlinked files block before another download. Abrupt termination before hashes save (SIGKILL or power loss) still requires inspection. Other partial outputs remain blocked; never delete them blindly. Successful repeated preparation and capture reuse their recorded outputs.

For an **existing helper-owned workspace completed manually**, use explicit recovery—not hash edits or another download:

```bash
python3 scripts/media-prep.py recover local/summaries/four-to-six-title-words \
  --source 'EXACT_RECORDED_SOURCE' --archive-sha256 'INSPECTED_FINAL_ARCHIVE_SHA256' \
  --subtitles local/transcripts/VIDEO_ID.en.srt \
  --provenance local/transcripts/VIDEO_ID.en.json3
```

Inspect source identity and archive first; the supplied hash binds that decision, not proof of remote origin. Recovery requires the retained `<id>.pre-subs.mkv`, original metadata and timestamped transcript, an original SRT, and identical copies beside the archive. Optional `--provenance` lists extra original sidecars to verify and record. Originals must be in that source's transcript/prep workspace. Recovery checks existing ownership hashes, source/duration, original media packets, embedded subtitle text/timing, transcript content/timestamps and provenance before updating only the manifest. It cannot repair changed recorded files or adopt an unowned directory. Failure preserves files and manifest; unrelated files and historical partials remain untouched and unadopted. Resume afterward without `--subtitles`, or supply the SRT path used for recovery.

Initial local remux checks stream properties and packet payloads, allowing up to one second of container duration change (for example, AAC priming timestamps). Subtitle embedding uses stricter checks: unchanged original packet payloads and PTS/DTS/durations, matching subtitle cues, and at most 50 ms overall duration change. Original subtitle bytes are preserved; cue comparison permits ffmpeg's removal of leading cue whitespace. A verified candidate replaces only the helper-owned archive, retaining `<id>.pre-subs.mkv`. No explicit cleanup or publishing command exists. yt-dlp may remove its own component streams after a successful merge.

Hash checks read every recorded artifact; packet comparison holds one stream's packet listing in memory. This favors conservative verification over fast resume for large recordings. No latency or quality improvement is claimed.

## Output

Each summary lives in its own directory under `local/summaries/`:

```
local/summaries/<slug>/
├── <id>.md          # the summary
├── <id>.mkv         # archival video with subtitles
├── <id>.meta.json   # local source provenance; do not publish
├── <id>.transcript.txt
├── <id>.asr.srt     # or original source subtitle files
└── images/          # captured slides and diagrams
    ├── slide-01-*.jpg
    └── ...
```

## Examples

- [Frontier Operations: The Five Skills Behind Tiny Teams Beating Giant Ones](https://gist.github.com/stvhay/d2a1d6f6e1168ec6c4f6eacfe820e537) — YouTube monologue, text-only summary
- [Beyond Interpolation: Automated Discovery of Symmetry Groups via Tensor Factorization](https://gist.github.com/stvhay/5f459eb0d90f929fcc89d51023969bc8) — academic lecture with slide captures and references

## How it works

`CLAUDE.md` owns workflow decisions, summary standards, and failure handling. The Pi skill points to it rather than maintaining a second workflow.

- `scripts/yt-dlp.sh`: refreshes and runs the official GitHub nightly through uv for online work.
- `scripts/archive.conf`: native yt-dlp quality-first selection and Matroska output policy.
- `scripts/verify-archive.sh`: read-only structural check; requires video, audio, and subtitles by default. Does not prove full decode or subtitle fidelity.
- `scripts/media-prep.py`: source-owned mechanical preparation, candidate capture and read-only verification.
- `tests/check-workflow.sh`: offline regression checks using synthetic formats and tiny media files.
- `tests/check-media-prep.py`: preparation/resume/conflict checks with real ffmpeg/ffprobe and yt-dlp on loopback HTTP. A fake uv checks launcher arguments and refresh failure without Internet access; a fake Whisper checks only the ASR command/output contract.

Run `bash tests/check-workflow.sh` and `python3 tests/check-media-prep.py`. No Internet, new test framework, or existing local media required. Live hosts and real ASR quality are not covered by these checks.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution workflow. This project uses Claude Code skills to maintain quality — the skills ship with the repo.

## License

[MIT](LICENSE)
