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
brew install yt-dlp ffmpeg imagemagick mkvtoolnix
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

- `scripts/archive.conf`: native yt-dlp quality-first selection and Matroska output policy.
- `scripts/verify-archive.sh`: read-only structural check; requires video, audio, and subtitles by default. Does not prove full decode or subtitle fidelity.
- `tests/check-workflow.sh`: offline regression checks using synthetic formats and tiny media files.

Run checks with `bash tests/check-workflow.sh`. No network, new test framework, or existing local media required.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution workflow. This project uses Claude Code skills to maintain quality — the skills ship with the repo.

## License

[MIT](LICENSE)
