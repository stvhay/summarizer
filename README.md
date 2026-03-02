# Video Summarizer

Turn any video into a structured markdown summary thorough enough to replace watching it.

This is a [Claude Code](https://docs.anthropic.com/en/docs/claude-code) workflow — not a traditional codebase. The project is a Nix dev environment plus a detailed `CLAUDE.md` that instructs Claude Code to fetch transcripts, write summaries, capture slides, archive video, verify facts against primary sources, and publish to GitHub Gist. You provide a URL; Claude Code does the rest.

## Prerequisites

- [Nix](https://nixos.org/download/) (with flakes enabled)
- [direnv](https://direnv.net/) (hooks into your shell to auto-load the environment)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (Anthropic's CLI agent)

## Setup

```bash
git clone https://github.com/stvhay/summarizer.git
cd summarizer
direnv allow    # installs yt-dlp, ffmpeg, imagemagick, mkvtoolnix
```

Then start Claude Code:

```bash
claude
```

## Usage

Paste a video URL and Claude Code follows the workflow defined in `CLAUDE.md`:

1. Fetches metadata and subtitles via `yt-dlp`
2. Converts subtitles to a readable transcript
3. Writes a structured summary with the speaker's own framework
4. Verifies claims against primary sources (for academic/technical talks)
5. Extracts and optimizes key slides and diagrams
6. Archives highest-quality video+audio as `.mkv`
7. Applies a copy-editing pass (Strunk & White's *Elements of Style*)
8. Optionally publishes to GitHub Gist

Works with YouTube, archive.org, and any other site [yt-dlp supports](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

## Output

Each summary lives in its own directory under `summaries/`:

```
summaries/<slug>/
├── <id>.md          # the summary
├── <id>.mkv         # archival video
└── images/          # captured slides and diagrams
    ├── slide-01-*.jpg
    └── ...
```

## Examples

- [Frontier Operations: The Five Skills Behind Tiny Teams Beating Giant Ones](https://gist.github.com/stvhay/d2a1d6f6e1168ec6c4f6eacfe820e537) — YouTube monologue, text-only summary
- [Beyond Interpolation: Automated Discovery of Symmetry Groups via Tensor Factorization](https://gist.github.com/stvhay/5f459eb0d90f929fcc89d51023969bc8) — academic lecture with slide captures and references

## How it works

The entire workflow lives in `CLAUDE.md`. There's no application code — Claude Code reads the instructions and executes them using shell tools (`yt-dlp`, `ffmpeg`, `imagemagick`) provided by the Nix environment. The instructions encode operational knowledge: how to handle archive.org's subtitle quirks, when to prefer AV1 over H.264, how to catch ASR errors in math-heavy talks by cross-referencing the source paper.

`CLAUDE.md` is both the documentation and the program.

## License

[MIT](LICENSE)
