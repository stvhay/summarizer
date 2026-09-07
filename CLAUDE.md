# Video Summarization Project

## Purpose

Extract and summarize video content into structured markdown documents using `yt-dlp`. Sources include YouTube, archive.org, and any other site yt-dlp supports. The goal is a document thorough enough that reading it replaces watching the video.

## First-Run Setup

On first use in a fresh clone, follow `docs/FIRST_RUN.md` to initialize project memory files.

## Environment

- **Dependencies**: Nix packages live in `flake.nix` (`buildInputs`). Homebrew setup is maintained separately in `README.md`; do not require identical package lists.
- **Initialization**: `.envrc` uses the Nix flake when available; otherwise it checks core tools. It then runs scripts from `.envrc.d/` and `.envrc.local.d/`.
- **Online yt-dlp**: Use `bash scripts/yt-dlp.sh` for metadata, downloads, subtitles and format inspection. It requires uv and refreshes the latest official GitHub nightly in an isolated Python environment on each invocation. Do not fall back to the older Nix/Homebrew yt-dlp if refresh fails. The packaged binary remains for offline tests; local preparation and completed resume need no refresh. See README for runtime requirements.
- **Optional capabilities**: Before local transcription, check `command -v whisper-cli` and the model file. Before publishing, check `command -v gh` and authentication. If unavailable, preserve progress and request setup; do not silently skip the step.
- `.envrc.d/setup.sh` creates `local/inbox/`, `local/transcripts/`, `local/summaries/`, and `local/models/` and exports their directory paths.
- These directories are **local working directories** — not tracked in git. They're created on first `direnv allow`.
- If you add a dependency to `flake.nix`, ask the user to restart the session so `direnv` reloads.

## Workflow

This is the canonical workflow for every agent entry point. Run commands from the repository root; replace placeholders with quoted paths and URLs.

If the request does not name a source, inspect `local/inbox/` before requesting input. Scope every mutation to that source. Preserve unrelated instructions, models, transcripts, summaries, and local media. If input, access, or a required tool is unavailable, preserve partial work and request what is missing rather than bypassing the workflow.

1. **Identify the source and destination.** Fetch online metadata with `bash scripts/yt-dlp.sh --no-playlist --dump-json --no-download "<url>"`; save it as `local/transcripts/<id>.meta.json` after identifying the video ID. For local files, choose a stable ID and record the original filename, available title/speaker/date/source URL, and `ffprobe` duration in that JSON file; mark unknown fields rather than inventing them. Derive a 4–6-word lowercase hyphenated slug from the title and create `local/summaries/<slug>/`. Check existing files before writing: resume only a matching source; do not overwrite unrelated artifacts.
2. **Acquire the archive once** using **Archival Video Acquisition** below. Use that `.mkv` for ASR and frame extraction; preserve the original local input. A separate preview download is an exception only when archive size makes it necessary, not the default.
3. **Obtain subtitles.** Format depends on the source:
   - **YouTube**: JSON3 format (richer than VTT for parsing):
     ```bash
     bash scripts/yt-dlp.sh --no-playlist --write-subs --write-auto-sub --sub-lang en --sub-format json3 --skip-download -o "local/transcripts/<id>" "<url>"
     ```
   - **archive.org**: yt-dlp often doesn't detect archive.org subtitles. Check the item's download page (`https://archive.org/download/<id>/`) for `.srt` or `.vtt` files and download them directly with `curl`.
   - **Other sources**: Try `--write-auto-sub` first; fall back to `--write-sub` or direct download.
   - **Local files**: inspect embedded subtitle tracks first and extract a suitable text track with ffmpeg. Use ASR only if no usable subtitles exist.
   - **No subtitles anywhere** (login-walled sites, conference recordings, local files): check `whisper-cli` and the model are available, then transcribe locally. Extract 16 kHz mono audio from the archive:
     ```bash
     ffmpeg -n -i "local/summaries/<slug>/<id>.mkv" -vn -ac 1 -ar 16000 -c:a pcm_s16le "local/transcripts/<id>.wav"
     whisper-cli -m local/models/ggml-large-v3-turbo.bin -f local/transcripts/<id>.wav \
       -l en -t 8 -osrt -of local/transcripts/<id>.asr
     ```
     Runs ~10x realtime. Models live in `local/models/` (untracked) — download from [ggerganov/whisper.cpp](https://huggingface.co/ggerganov/whisper.cpp) if missing. **ASR output is noisy**: treat every proper noun and technical term as suspect and correct it against slides and primary sources during the factual accuracy review. Name ASR transcripts `<id>.asr.srt` to distinguish them from real subtitles.
4. Convert subtitles to a readable timestamped transcript. For JSON3, extract `events[].segs[].utf8` and compute timestamps from `tStartMs`. For SRT/VTT, parse timestamp lines and text blocks. Save as `local/transcripts/<id>.transcript.txt`.
5. **Preserve provenance and embed subtitles** using the instructions below. Keep metadata, readable transcript, and original subtitles (including `.asr.srt`) beside the summary. Generated ASR is not re-downloadable.
6. Read the full transcript, choose the dominant **Summary Profile**, and write `local/summaries/<slug>/<id>.md`. For mixed material, use the dominant structure and apply academic/technical rigor where needed.
7. **Factual accuracy review** for academic/technical lectures, then **visual review and screen capture** from the archive (see below).
8. After structure, claims, attribution, and quotations are stable, run `/writing-clearly-and-concisely` once as the final editing pass. Recheck quote fidelity, attribution, metadata, links, and chronological timestamp order; copy-editing must not change meaning or navigation.
9. **Verify before cleanup.** Run the archive check below, review the summary and image links, and compare preserved provenance files against their originals with `cmp`. Only then remove an explicit list of this run's disposable files (WAV, candidate frames, and verified duplicate sidecars). Do not use an ID-prefix deletion glob. On any failure, preserve intermediates and the original archive; report incomplete work.

### Optional mechanical helper

`scripts/media-prep.py` provides `prepare`, `capture`, and read-only `verify`; see [README.md](README.md#mechanical-preparation-helper) for the CLI and Python 3.11+ prerequisite. It uses the shared archive policy, source-owned workspaces, source subtitles before ASR, preserved provenance, verified embedding, and batched candidate captures. Use it only for new helper-owned workspaces, not to adopt or alter existing manual archives.

A successful helper result completes mechanical preparation only. Still read the full transcript, choose a profile, review primary sources and visuals, write the summary, and perform the final editing and summary/link checks above. Its manifest and logs are local/private. Blocked results preserve partial work; follow the reported conflict or prerequisite instead of bypassing it. The helper never performs the final cleanup or publishes anything.

## Summary Profiles

Choose structure by content, not platform. Do not force one template onto every video.

### Interviews, News, Podcasts, and Informative Videos

Optimize for comprehension and scanning rather than a minute-by-minute retelling.

- Lead with one compact `## Bottom line`, usually four to six items. Give each item a standalone bold thesis followed by a separate short explanation. Do not repeat the same synthesis in an executive summary or closing section.
- Organize the detailed body around the conversation's main claims and tensions. Preserve attribution, disagreement, uncertainty, disclosures, recommendations, and concrete examples.
- Put selective timestamp links in the corresponding major section headings, such as `## Autonomous agents cross a line · [13:05](...)`. Mark substantive transitions; skip sponsor breaks and minor asides. Add a separate chapter list only when requested.
- Quote sparingly and verify every blockquote against the transcript. Paraphrase the rest.
- Verify independently checkable claims when their truth affects the summary. If verification is unnecessary or unavailable, attribute the claim to the speaker instead of presenting it as established fact.
- Include visuals only when they convey information absent from the conversation, such as a chart, diagram, slide, or significant on-screen text. Omit talking heads, studio shots, and decorative frames.

### Academic Lectures and Technical Presentations

Prioritize precision and explanatory completeness over inverted-pyramid brevity.

- Do not force the interview/news `Bottom line` format when concepts depend on earlier definitions. A short orientation may precede a body organized by the lecture's or paper's logical structure.
- Preserve definitions, assumptions, notation, methods, evidence, results, and limitations. Distinguish proved results, experimental findings, conjectures, speculation, and the speaker's interpretation.
- Apply the primary-source factual review below. Technical accuracy, result status, and references outrank compression.
- Capture equations, diagrams, tables, and slides when the prose alone would not make the explanation self-contained.

## Factual Accuracy Review (Academic/Technical Lectures)

For academic lectures, conference talks, and technical presentations, verify the summary against primary sources **before** the copy-editing pass. The summary must be faithful to what the speaker actually proved, claimed, or conjectured — not introduce errors through paraphrase.

### When to apply

Apply this step when the video is an academic lecture, seminar, conference talk, or technical presentation where the speaker references specific papers, theorems, or experimental results. Skip for casual interviews, podcasts, and opinion-driven content.

### Process

1. **Identify cited works.** Extract paper titles, author names, and years mentioned in the transcript or visible on slides. Search for the primary paper(s) underlying the talk — the speaker's own work and key references.
2. **Retrieve and read the paper** (or abstract + key results) using web search. ArXiv, Semantic Scholar, and Google Scholar are the best sources. If the paper isn't publicly available, note this and work from the abstract.
3. **Cross-reference claims.** For each major claim in the summary, verify:
   - Do the theorems, lemmas, and definitions match the paper?
   - Are experimental results (numbers, comparisons, baselines) accurately represented?
   - Are conjectures clearly distinguished from proven results?
   - Are limitations acknowledged faithfully?
4. **Correct errors.** Fix any misstatements introduced during transcript-to-summary conversion. ASR transcripts garble technical terms (e.g., "Kaylee table" for "Cayley table," "eReps" for "irreps"). Cross-referencing catches these.
5. **Add a References section** at the end of the summary. Include:
   - The speaker's own paper(s) with arXiv IDs and a one-line description of each.
   - Key cited prior works (author, year, title, arXiv ID where available).
   - This gives readers a path to the primary sources and grounds the summary in verifiable literature.

### Why this matters

ASR transcripts of math-heavy talks are noisy. A speaker says "Cauchy-Schwarz" and the transcript writes "cautious rush." The summary writer (you) must recognize these errors and correct them. The only reliable way is to read the actual paper and verify the math tracks.

## Visual Review and Screen Capture

After writing the summary, review the video for visuals that carry information the prose cannot efficiently preserve (slides, charts, diagrams, screen shares, on-screen text/graphics). Captures should make the summary more self-contained, not decorate it.

### Process

1. **Reuse the archive** at `local/summaries/<slug>/<id>.mkv`. Do not download a second video for routine frame extraction.
2. **Sample frames** — extract ~10-12 evenly spaced frames across the video using ffmpeg. Use Claude vision to review them and determine the visual style (talking head, slides, mixed, screenshare, etc.).
3. **Decide whether captures are needed.** Skip talking heads, studio shots, and visuals that merely illustrate what the conversation already says; note "No visual content to capture" in the process. For academic and technical material, retain legible equations, diagrams, result tables, and slides needed to follow the argument.
4. **If visuals exist**, cross-reference the transcript to identify timestamps where key visual content appears (slide transitions, chart displays, diagram reveals, significant on-screen text). Extract candidate frames at those timestamps:
   ```bash
   ffmpeg -n -ss <timestamp> -i "local/summaries/<slug>/<id>.mkv" -frames:v 5 -q:v 2 "local/transcripts/<id>.candidate-<timestamp>_%03d.jpg"
   ```
   Extract a short burst (~5 frames) around each timestamp to avoid capturing mid-transition or blurred frames.
5. **Select best frames** using Claude vision. Pick the sharpest, most legible frame for each visual. Reject duplicates and near-duplicates.
6. **Optimize images** with ImageMagick — strip metadata, resize if needed, convert to efficient format:
   ```bash
   magick input.jpg -strip -quality 85 -resize '1280x>' output.jpg
   ```
7. **Save to `images/` subfolder** relative to the summary `.md` file, using descriptive filenames:
   ```
   local/summaries/<slug>/images/slide-01-bubble-diagram.jpg
   local/summaries/<slug>/images/chart-02-revenue-per-employee.jpg
   ```
8. **Insert image references** in the markdown summary at the appropriate location:
   ```markdown
   ![Bubble diagram showing expanding AI capability frontier](images/slide-01-bubble-diagram.jpg)
   ```
9. Retain the archive permanently. Remove candidate frames only during the final verified cleanup step.

## Archival Video Acquisition

Acquire video and audio once, as Matroska, before ASR or visual extraction. Keep the archive alongside the summary permanently.

### Online sources

Use the same command for YouTube, archive.org, and other yt-dlp-supported hosts:

```bash
bash scripts/yt-dlp.sh --ignore-config --config-locations scripts/archive.conf \
  -o "local/summaries/<slug>/<id>.%(ext)s" "<url>"
```

`scripts/archive.conf` selects separate best video/audio streams with a combined-stream fallback. It forces Matroska remuxing even when no merge is needed; an `.mkv` filename alone does not prove the container. The config processes one video, not an entire playlist. Pass any needed authentication options explicitly; user-wide yt-dlp settings are ignored for predictable selection.

**Quality before codec:** resolution, frame rate, dynamic range, bitrate, audio sample rate, and channels precede codec preferences. At equal reported quality, yt-dlp prefers AV1 over VP9 over H.265/H.264 and Opus over AAC. Reported bitrate is only a proxy, not a cross-codec perceptual-quality measurement. Inspect `bash scripts/yt-dlp.sh -F "<url>"` when metadata is incomplete or misleading; record any deliberate format override in the preserved metadata.

### Local files and login-walled recordings

For unsupported/login-walled hosts, ask for a local download rather than bypassing access controls. Inspect the local file with `ffprobe`, then remux without changing the original:

```bash
ffmpeg -n -i "<local-video>" -map 0 -c copy "local/summaries/<slug>/<id>.mkv"
```

If the input is already the matching archive, reuse it. If a codec cannot be muxed into Matroska, convert only the incompatible track (for example, a text subtitle to SRT); do not silently discard streams. Keep original input untouched on failure. Confirm video/audio streams before using the archive; subtitles may be added after transcription.

### Preserve provenance and embed subtitles

Keep these files beside the summary, retaining their original names:

- `<id>.meta.json`: source metadata, including any local-source details and deliberate overrides.
- `<id>.transcript.txt`: the readable timestamped transcript used for the summary.
- Original subtitle files: JSON3, VTT, SRT, and/or `<id>.asr.srt`. Preserve original ASR separately from corrections.

Copy exact files without overwriting existing provenance, then verify each copy with `cmp`. Do not proceed if an existing destination differs. Metadata can contain signed URLs or other private source details; keep it local, not in the gist.

For embedding, use SRT. Convert VTT with ffmpeg. For YouTube JSON3, retain the JSON3 and request an embeddable version without downloading video again:

```bash
bash scripts/yt-dlp.sh --no-playlist --write-subs --write-auto-sub --sub-lang en \
  --sub-format "srt/vtt/best" --convert-subs srt --skip-download \
  -o "local/transcripts/<id>" "<url>"
```

If no embeddable version is available, convert the existing transcript's timed cues to SRT and verify text/timing before embedding; do not discard the source. An ASR `.srt` already works. Use the track corresponding to the transcript; an unrelated existing subtitle does not satisfy preservation.

Add that SRT to a new candidate archive, preserving existing streams:

```bash
ffmpeg -n -i "local/summaries/<slug>/<id>.mkv" -i "<preserved-subtitle.srt>" \
  -map 0 -map 1:0 -c copy "local/summaries/<slug>/<id>.with-subs.mkv"
bash scripts/verify-archive.sh "local/summaries/<slug>/<id>.with-subs.mkv"
```

After the command succeeds, inspect the added track's text and timing against the preserved sidecar and compare candidate duration/streams with the original. Only after those checks pass, replace the original archive with the verified candidate. Do not overwrite an existing candidate; inspect it for resumption first. If the matching subtitle is already embedded and verified, skip the remux.

### Verification and cleanup gate

```bash
bash scripts/verify-archive.sh "local/summaries/<slug>/<id>.mkv"
```

The read-only check requires a nonempty, probeable Matroska file with video, audio, and subtitle streams. It is a structural check, not a full decode or a subtitle-fidelity check. Also check duration against the source, confirm the correct subtitle track, and inspect playback if corruption is suspected.

Use `--no-subtitles` only when no usable subtitles exist, transcription is unavailable, and the user explicitly accepts a subtitle-free archive. Record that exception; it does not waive the transcript requirement for a completed summary. Missing subtitles otherwise block cleanup.

After this gate and the summary/provenance checks in **Workflow**, delete only the explicit disposable paths from this run. Retain the archive, metadata, transcript, subtitle sidecars, summary, and selected images:

```text
local/summaries/<slug>/
├── <id>.md
├── <id>.mkv
├── <id>.meta.json
├── <id>.transcript.txt
├── <id>.asr.srt          # or source subtitle files
└── images/
```

## Publishing to GitHub Gist

Optionally publish a finished summary as a GitHub Gist. See `docs/PUBLISHING_GIST.md` for the full process.

Key constraints: gists don't support directories (images go at root), use absolute `gist.githubusercontent.com/<user>/<gist-id>/raw/<filename>` URLs for images, use the slug as the gist filename, and use `"Video Summary"` as the description.

## Writing Standards

- Front matter: title, source URL, speaker, date, duration.
- Structured with headers, bullet points, and occasional blockquotes for key statements.
- For multiple major parts, include a contents list with labels matching major-part headings and links to stable anchors (explicit anchors where generated fragments would be fragile). Keep document links distinct from source-video timestamps. Related summaries use one document-title pattern and one basis for major-part titles. Skip the contents list for short single-part summaries.
- Capture all substantive claims, frameworks, advice, and examples.
- Use the speaker's own language for key terms and phrases; quote only wording verified against the transcript.
- Preserve concrete examples — they're the difference between "I get it" and "I could explain it."
- No filler or padding. Dense, scannable, useful.

## Lessons Learned

- **Auto-generated subs are usually the only option.** Most YouTube videos don't have manually uploaded subtitles. `--write-auto-sub` is the right default.
- **Structure the summary around the speaker's own framework.** Don't impose a generic template. If the speaker has a clear structure, follow it. The summary should feel like a compression of the talk, not a book report about it.
- **Blockquote the best lines verbatim.** The speaker's phrasing often carries meaning that paraphrasing would lose. Pull direct quotes for punchy or precise statements.
- **archive.org item IDs work as yt-dlp video IDs.** The archive.org identifier (e.g., `redwood-center-2026-02-11-ben-dongsung-huh`) serves as the `<id>` throughout the workflow. Use `https://archive.org/details/<id>` as the URL for yt-dlp.
- **Verify academic summaries against the source paper before copy-editing.** ASR transcripts garble technical terms ("Kaylee table" for "Cayley table," "eReps" for "irreps"). Cross-reference the actual paper before the Strunk & White pass — fixing factual errors after prose is polished wastes effort.
- **Login-walled sources need a manual download.** Conference sites (e.g. VSS) serve recordings only to members, and `--cookies-from-browser` won't help when yt-dlp has no extractor for the page. Ask the user to download the file in their browser, then run the workflow against the local file. Everything downstream is unchanged except that subtitles must come from ASR.
- **For multi-talk session recordings, find talk boundaries visually, not by guessing.** Sample frames across the recording (every ~4 min) into a labeled contact sheet with `ffmpeg` + `magick montage`, then read the title and "Thank you" slides to bracket each talk. Confirm against the published talk times: recording 00:00 usually maps to the session's advertised start, so a talk at 11:15 in a session starting at 10:45 sits near 00:30:00. Cut the audio for one talk instead of transcribing the whole session.
- **Extract slides from the montage timestamps, then verify.** Slide timings read off a contact sheet are approximate, and short slides are easy to overshoot — re-check each extracted frame and re-sample at finer granularity where it landed on the wrong slide or mid-transition.
- **The delivered talk can diverge from the published abstract.** VSS 22.23 presented seven experiments where its abstract described six, and the abstract's stimulus counts were never stated aloud. Follow the talk, and record the discrepancy in the summary rather than silently reconciling it.
- **Check whether conference work is actually published.** A VSS abstract is author-supplied and unreviewed. Say so explicitly, and don't credit a talk with novelty that a cited prior paper already established.

## Contributing

Follow [CONTRIBUTING.md](CONTRIBUTING.md). Scale planning and review to the change; publishing a PR is separate from local implementation.
