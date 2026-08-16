# Video Summarization Project

## Purpose

Extract and summarize video content into structured markdown documents using `yt-dlp`. Sources include YouTube, archive.org, and any other site yt-dlp supports. The goal is a document thorough enough that reading it replaces watching the video.

## First-Run Setup

On first use in a fresh clone, follow `docs/FIRST_RUN.md` to initialize project memory files.

## Environment

- **Dependencies**: Managed via `flake.nix`. Add packages to `buildInputs`.
- **Initialization**: `.envrc` sources `use flake` and runs scripts from `.envrc.d/` and `.envrc.local.d/`.
- `.envrc.d/setup.sh` creates `local/inbox/`, `local/transcripts/`, `local/summaries/`, and `local/models/` and exports their directory paths.
- These directories are **local working directories** — not tracked in git. They're created on first `direnv allow`.
- If you add a dependency to `flake.nix`, ask the user to restart the session so `direnv` reloads.

## Workflow

If the request does not name a source, inspect `local/inbox/` before requesting input.

1. Fetch video metadata: `yt-dlp --dump-json --no-download <url> > local/transcripts/<id>.meta.json`
   - For archive.org, redirect stderr (`2>/dev/null`) as yt-dlp emits harmless warnings about non-numeric fields.
2. Download subtitles. Format depends on the source:
   - **YouTube**: JSON3 format (richer than VTT for parsing):
     ```bash
     yt-dlp --write-auto-sub --sub-lang en --sub-format json3 --skip-download -o "local/transcripts/%(id)s" <url>
     ```
   - **archive.org**: yt-dlp often doesn't detect archive.org subtitles. Check the item's download page (`https://archive.org/download/<id>/`) for `.srt` or `.vtt` files and download them directly with `curl`.
   - **Other sources**: Try `--write-auto-sub` first; fall back to `--write-sub` or direct download.
   - **No subtitles anywhere** (login-walled sites, conference recordings, local files): transcribe locally with `whisper-cpp`. Extract 16 kHz mono audio, then run the model:
     ```bash
     ffmpeg -i <video> -vn -ac 1 -ar 16000 -c:a pcm_s16le local/transcripts/<id>.wav
     whisper-cli -m local/models/ggml-large-v3-turbo.bin -f local/transcripts/<id>.wav \
       -l en -t 8 -osrt -of local/transcripts/<id>.asr
     ```
     Runs ~10x realtime. Models live in `local/models/` (untracked) — download from [ggerganov/whisper.cpp](https://huggingface.co/ggerganov/whisper.cpp) if missing. **ASR output is noisy**: treat every proper noun and technical term as suspect and correct it against slides and primary sources during the factual accuracy review. Name ASR transcripts `<id>.asr.srt` to distinguish them from real subtitles.
3. Convert subtitles to a readable timestamped transcript. For JSON3, extract `events[].segs[].utf8` and compute timestamps from `tStartMs`. For SRT, parse timestamp lines and text blocks. Save as `local/transcripts/<id>.transcript.txt`.
4. Read the full transcript, then choose the dominant **Summary Profile** below. For mixed material, use the dominant structure and apply academic/technical rigor to sections that need it.
5. Derive a human-readable slug from the video title (lowercase, hyphens, 4-6 key words — e.g., `frontier-operations-five-skills-tiny-teams`). Create a directory `local/summaries/<slug>/` and write the summary to `local/summaries/<slug>/<id>.md`.
6. **Factual accuracy review** (for academic/technical lectures — see details below).
7. **Visual review and screen capture** (see details below).
8. **Archive video** — download highest-quality video+audio as `.mkv` (see details below).
9. After the structure, claims, attribution, and quotations are stable, run `/writing-clearly-and-concisely` once as the final editing pass. Then recheck quote fidelity, attribution, metadata, links, and chronological timestamp order; copy-editing must not change meaning or navigation.
10. **Clean up transcript artifacts** — remove all intermediate files for this video from `local/transcripts/`:
    ```bash
    rm -f local/transcripts/<id>.*
    ```
    The metadata, subtitles, and plaintext transcript are all re-downloadable. Subtitles are embedded in the archival `.mkv`.

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

1. **Download the video** at up to 1080p for frame extraction:
   ```bash
   yt-dlp -f "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]" \
     -o "local/transcripts/<id>.video.mp4" --merge-output-format mp4 <url>
   ```
2. **Sample frames** — extract ~10-12 evenly spaced frames across the video using ffmpeg. Use Claude vision to review them and determine the visual style (talking head, slides, mixed, screenshare, etc.).
3. **Decide whether captures are needed.** Skip talking heads, studio shots, and visuals that merely illustrate what the conversation already says; note "No visual content to capture" in the process. For academic and technical material, retain legible equations, diagrams, result tables, and slides needed to follow the argument.
4. **If visuals exist**, cross-reference the transcript to identify timestamps where key visual content appears (slide transitions, chart displays, diagram reveals, significant on-screen text). Extract candidate frames at those timestamps:
   ```bash
   ffmpeg -ss <timestamp> -i local/transcripts/<id>.video.mp4 -frames:v 5 -q:v 2 /tmp/candidate_%03d.jpg
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
9. **Clean up** — delete the downloaded video file (`local/transcripts/<id>.video.mp4`) after extraction. Videos are large and re-downloadable; keep only the optimized images.

## Archival Video Download

Download the highest-quality video and audio, packaged as a `.mkv` file stored alongside the summary. This preserves a local archival copy.

### Codec preferences

Prefer open codecs (AV1 > VP9 for video, Opus for audio) when they match or exceed the quality of patent-encumbered alternatives. But **quality wins over ideology** — if the source only serves H.264/AAC (common on archive.org and many non-YouTube hosts), or if H.264/H.265 is available at significantly higher resolution or bitrate than the open alternatives, use the higher-quality option. The MKV (Matroska) container accepts any codec.

Format priority when choosing: **highest quality first**, with open codecs as tiebreaker:
1. AV1+Opus (open, best compression)
2. VP9+Opus (open, good compression)
3. H.265/HEVC+Opus or AAC (better compression than H.264)
4. H.264+AAC (universal fallback)

### Process

#### YouTube (open formats usually available)

1. **Download with open-format preference and embedded subtitles.** Video and audio are often separate streams on YouTube and must be downloaded independently and muxed together:
   ```bash
   yt-dlp \
     -f "bestvideo[vcodec^=av01]+bestaudio[acodec=opus]/bestvideo[vcodec^=vp9]+bestaudio[acodec=opus]/bestvideo[vcodec^=av01]+bestaudio/bestvideo[vcodec^=vp9]+bestaudio/bestvideo+bestaudio" \
     --write-auto-sub --sub-lang en --embed-subs \
     --merge-output-format mkv \
     -o "local/summaries/<slug>/<id>.mkv" <url>
   ```
   The trailing `bestvideo+bestaudio` fallback ensures you still get the best available even if no open codecs are served.

#### archive.org (typically H.264 only)

archive.org usually serves a single H.264 MP4. yt-dlp handles it, but subtitles need manual embedding:

1. **Download the video:**
   ```bash
   yt-dlp -f "bestvideo+bestaudio/best" \
     --merge-output-format mkv \
     -o "local/summaries/<slug>/<id>.mkv" <url>
   ```
2. **Embed subtitles separately** if you downloaded SRT/VTT files in the transcript step:
   ```bash
   ffmpeg -i "local/summaries/<slug>/<id>.mkv" -i "local/transcripts/<id>.srt" \
     -c copy -c:s srt "local/summaries/<slug>/<id>_with_subs.mkv"
   mv "local/summaries/<slug>/<id>_with_subs.mkv" "local/summaries/<slug>/<id>.mkv"
   ```

#### Other sources

Use `yt-dlp -f "bestvideo+bestaudio/best" --merge-output-format mkv` as the general fallback. Check if subtitles need manual embedding.

### Verification

Confirm the file exists and inspect streams:
```bash
ffprobe -hide_banner "local/summaries/<slug>/<id>.mkv"
```
Expect a video stream, an audio stream, and (if subtitles were embedded) a subtitle stream.

### No cleanup needed

Unlike the screen-capture video (which is temporary), the archival `.mkv` is the point. It stays in the summary directory permanently.

### Output

The `.mkv` file lives alongside the summary markdown:
```
local/summaries/<slug>/
├── <id>.md
├── <id>.mkv
└── images/
    └── ...
```

## Publishing to GitHub Gist

Optionally publish a finished summary as a GitHub Gist. See `docs/PUBLISHING_GIST.md` for the full process.

Key constraints: gists don't support directories (images go at root), use absolute `gist.githubusercontent.com/<user>/<gist-id>/raw/<filename>` URLs for images, use the slug as the gist filename, and use `"Video Summary"` as the description.

## Writing Standards

- Front matter: title, source URL, speaker, date, duration.
- Structured with headers, bullet points, and occasional blockquotes for key statements.
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

All changes follow the workflow in [CONTRIBUTING.md](CONTRIBUTING.md). File a GitHub issue, use the bundled skills to brainstorm, plan, execute, verify, and review, then open a PR with the plan and issue reference.
