# Video Summarization Project

## Purpose

Extract and summarize video content into structured markdown documents using `yt-dlp`. Sources include YouTube, archive.org, and any other site yt-dlp supports. The goal is a document thorough enough that reading it replaces watching the video.

## Environment

- **Dependencies**: Managed via `flake.nix`. Add packages to `buildInputs`.
- **Initialization**: `.envrc` sources `use flake` and runs scripts from `.envrc.d/` and `.envrc.local.d/`.
- `.envrc.d/setup.sh` creates `transcripts/` and `summaries/` and exports `$TRANSCRIPTS_DIR` and `$SUMMARIES_DIR`.
- Both directories are **local working directories** — not tracked in git. They're created on first `direnv allow` and can be regenerated from YouTube at any time.
- If you add a dependency to `flake.nix`, ask the user to restart the session so `direnv` reloads.

## Workflow

1. Fetch video metadata: `yt-dlp --dump-json --no-download <url> > transcripts/<id>.meta.json`
   - For archive.org, redirect stderr (`2>/dev/null`) as yt-dlp emits harmless warnings about non-numeric fields.
2. Download subtitles. Format depends on the source:
   - **YouTube**: JSON3 format (richer than VTT for parsing):
     ```bash
     yt-dlp --write-auto-sub --sub-lang en --sub-format json3 --skip-download -o "transcripts/%(id)s" <url>
     ```
   - **archive.org**: yt-dlp often doesn't detect archive.org subtitles. Check the item's download page (`https://archive.org/download/<id>/`) for `.srt` or `.vtt` files and download them directly with `curl`.
   - **Other sources**: Try `--write-auto-sub` first; fall back to `--write-sub` or direct download.
3. Convert subtitles to a readable timestamped transcript. For JSON3, extract `events[].segs[].utf8` and compute timestamps from `tStartMs`. For SRT, parse timestamp lines and text blocks. Save as `transcripts/<id>.transcript.txt`.
4. Read the full transcript.
5. Derive a human-readable slug from the video title (lowercase, hyphens, 4-6 key words — e.g., `frontier-operations-five-skills-tiny-teams`). Create a directory `summaries/<slug>/` and write the summary to `summaries/<slug>/<id>.md`.
6. **Factual accuracy review** (for academic/technical lectures — see details below).
7. **Visual review and screen capture** (see details below).
8. **Archive video** — download highest-quality video+audio as `.mkv` (see details below).
9. Run `/writing-clearly-and-concisely` on the finished summary as a final editing pass.
10. **Clean up transcript artifacts** — remove all intermediate files for this video from `transcripts/`:
    ```bash
    rm -f transcripts/<id>.*
    ```
    The metadata, subtitles, and plaintext transcript are all re-downloadable. Subtitles are embedded in the archival `.mkv`.

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

After writing the summary, review the video for visual content worth including (slides, charts, diagrams, screen shares, on-screen text/graphics). Images make summaries self-contained — a reader shouldn't need to watch the video to see a referenced chart.

### Process

1. **Download the video** at up to 1080p for frame extraction:
   ```bash
   yt-dlp -f "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]" \
     -o "transcripts/<id>.video.mp4" --merge-output-format mp4 <url>
   ```
2. **Sample frames** — extract ~10-12 evenly spaced frames across the video using ffmpeg. Use Claude vision to review them and determine the visual style (talking head, slides, mixed, screenshare, etc.).
3. **Decide whether captures are needed.** If the video is pure talking-head with no on-screen visuals, skip extraction and note "No visual content to capture" in the process. Many YouTube videos (especially monologues and podcasts) have no capture-worthy visuals.
4. **If visuals exist**, cross-reference the transcript to identify timestamps where key visual content appears (slide transitions, chart displays, diagram reveals, significant on-screen text). Extract candidate frames at those timestamps:
   ```bash
   ffmpeg -ss <timestamp> -i transcripts/<id>.video.mp4 -frames:v 5 -q:v 2 /tmp/candidate_%03d.jpg
   ```
   Extract a short burst (~5 frames) around each timestamp to avoid capturing mid-transition or blurred frames.
5. **Select best frames** using Claude vision. Pick the sharpest, most legible frame for each visual. Reject duplicates and near-duplicates.
6. **Optimize images** with ImageMagick — strip metadata, resize if needed, convert to efficient format:
   ```bash
   magick input.jpg -strip -quality 85 -resize '1280x>' output.jpg
   ```
7. **Save to `images/` subfolder** relative to the summary `.md` file, using descriptive filenames:
   ```
   summaries/<slug>/images/slide-01-bubble-diagram.jpg
   summaries/<slug>/images/chart-02-revenue-per-employee.jpg
   ```
8. **Insert image references** in the markdown summary at the appropriate location:
   ```markdown
   ![Bubble diagram showing expanding AI capability frontier](images/slide-01-bubble-diagram.jpg)
   ```
9. **Clean up** — delete the downloaded video file (`transcripts/<id>.video.mp4`) after extraction. Videos are large and re-downloadable; keep only the optimized images.

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
     -o "summaries/<slug>/<id>.mkv" <url>
   ```
   The trailing `bestvideo+bestaudio` fallback ensures you still get the best available even if no open codecs are served.

#### archive.org (typically H.264 only)

archive.org usually serves a single H.264 MP4. yt-dlp handles it, but subtitles need manual embedding:

1. **Download the video:**
   ```bash
   yt-dlp -f "bestvideo+bestaudio/best" \
     --merge-output-format mkv \
     -o "summaries/<slug>/<id>.mkv" <url>
   ```
2. **Embed subtitles separately** if you downloaded SRT/VTT files in the transcript step:
   ```bash
   ffmpeg -i "summaries/<slug>/<id>.mkv" -i "transcripts/<id>.srt" \
     -c copy -c:s srt "summaries/<slug>/<id>_with_subs.mkv"
   mv "summaries/<slug>/<id>_with_subs.mkv" "summaries/<slug>/<id>.mkv"
   ```

#### Other sources

Use `yt-dlp -f "bestvideo+bestaudio/best" --merge-output-format mkv` as the general fallback. Check if subtitles need manual embedding.

### Verification

Confirm the file exists and inspect streams:
```bash
ffprobe -hide_banner "summaries/<slug>/<id>.mkv"
```
Expect a video stream, an audio stream, and (if subtitles were embedded) a subtitle stream.

### No cleanup needed

Unlike the screen-capture video (which is temporary), the archival `.mkv` is the point. It stays in the summary directory permanently.

### Output

The `.mkv` file lives alongside the summary markdown:
```
summaries/<slug>/
├── <id>.md
├── <id>.mkv
└── images/
    └── ...
```

## Publishing to GitHub Gist

Optionally publish a finished summary as a GitHub Gist for easy sharing.

### When to use

Gists work for both text-only and image-bearing summaries. For summaries with images, clone the gist repo, add images at the root (gists don't support directories), rewrite image paths to absolute `gist.githubusercontent.com/raw/` URLs, and push.

### Gist display conventions

GitHub Gist renders three prominent elements: the **filename** (as page title), the **description** (as a gray subtitle), and the **rendered markdown**. To avoid redundancy:

- **Filename**: `<slug>.md` — the human-readable slug, not the video ID. This becomes the gist's page title (e.g., `stvhay / frontier-operations-five-skills-tiny-teams.md`).
- **Description**: `"Video Summary"` — frames the genre for anyone landing on the gist. Static across all summaries.
- **Markdown H1**: The full human-readable title. This is the reader's entry point once they're in the document.

### Gist-adapted front matter

The canonical summary in `summaries/` uses a multi-line bold metadata block (Source, Speaker, Date, Duration). For gist display, adapt the front matter into a plain-text metadata block with explicit labels, linked author, and `<br>` line breaks. Do not use a blockquote — the left bar makes metadata look like a quotation.

```markdown
# Video Title Here

**Source**: [Original video title](https://source-url)<br>
**Author**: [Speaker Name](https://channel-or-profile-url) (Channel Name)<br>
**Date**: Month Day, Year<br>
**Length**: HH:MM

---
```

The `<br>` tags are required — without them, GitHub collapses consecutive lines into a single paragraph.

Fetch the author's channel/profile URL from video metadata (`yt-dlp --dump-json` → `uploader_url`). For academic talks, use ORCID or institutional page if available.

Write the adapted version to a temp file named `<slug>.md` for the gist — don't modify the canonical summary.

### Process (text-only)

1. **Create the gist-adapted file** at `/tmp/<slug>.md` — copy the summary, replace the multi-line front matter with the format above.
2. **Create the gist**:
   ```bash
   gh gist create --public \
     -d "Video Summary" \
     "/tmp/<slug>.md"
   ```
   Use `--public` for discoverable gists or omit for secret (URL-only) gists.
3. **Clean up** — delete `/tmp/<slug>.md`.

### Process (with images)

1. **Create the gist-adapted file** at `/tmp/<slug>.md` — same front matter adaptation as above, but keep `images/slide-*.jpg` references for now.
2. **Create the gist** with `gh gist create --public -d "Video Summary" "/tmp/<slug>.md"`.
3. **Clone the gist repo** to a temp directory:
   ```bash
   gh gist clone <gist-id> /tmp/gist-<slug>
   ```
4. **Copy images flat to the gist root** — gists reject pushes containing directories:
   ```bash
   cp summaries/<slug>/images/*.jpg /tmp/gist-<slug>/
   ```
5. **Rewrite image paths** in the markdown from `images/slide-` to absolute raw URLs:
   ```
   https://gist.githubusercontent.com/<user>/<gist-id>/raw/slide-
   ```
6. **Commit and push**:
   ```bash
   cd /tmp/gist-<slug> && git add -A && git commit -m "Add slide images" && git push
   ```
7. **Clean up** — delete `/tmp/gist-<slug>` and `/tmp/<slug>.md`.

### Notes

- **Gists don't support directories.** Image files must live at the repo root. The gist web UI lists them alongside the markdown, but they don't interfere with rendering.
- **Use absolute raw URLs for images.** `gist.githubusercontent.com/<user>/<gist-id>/raw/<filename>` resolves to the latest revision. Relative paths (`images/slide-...`) won't render.
- The `.mkv` archive is too large for gists. Gists are for the summary document only.

## Writing Standards

- Front matter: title, source URL, speaker, date, duration.
- Structured with headers, bullet points, and blockquotes for key statements.
- Capture all substantive claims, frameworks, advice, and examples.
- Use the speaker's own language for key terms and phrases.
- Preserve concrete examples — they're the difference between "I get it" and "I could explain it."
- No filler or padding. Dense, scannable, useful.

## Lessons Learned

- **Use `--sub-format json3` not VTT.** JSON3 gives structured segment data that's easy to parse programmatically. VTT requires more complex timestamp/cue parsing and the raw text is less clean.
- **Always fetch metadata separately** (`--dump-json --no-download`). Title, channel, upload date, description, and chapter markers are all in there and save you from guessing context.
- **Auto-generated subs are usually the only option.** Most YouTube videos don't have manually uploaded subtitles. `--write-auto-sub` is the right default. The transcript quality is good enough to work from.
- **Convert JSON3 to plaintext transcript as an intermediate step.** Reading raw JSON3 is painful. A simple Python script to extract text with timestamps makes the transcript human-readable and easier to work with.
- **Structure the summary around the speaker's own framework.** Don't impose a generic template. If the speaker has a clear structure (as most good talks do), follow it. The summary should feel like a compression of the talk, not a book report about it.
- **Blockquote the best lines verbatim.** The speaker's phrasing often carries meaning that paraphrasing would lose. Pull direct quotes for punchy or precise statements.
- **Use human-readable directory slugs.** Store each summary in `summaries/<slug>/<id>.md` where `<slug>` is a short hyphenated label derived from the title. Makes browsing summaries possible without memorizing YouTube IDs.
- **Run `/writing-clearly-and-concisely` as a final pass.** Dispatches a subagent with Strunk's *Elements of Style* to tighten prose: active voice, positive form, cut filler, place emphasis at sentence ends. Catches things you miss after staring at a draft too long.
- **Sample before extracting — most videos have no slides.** Many YouTube videos (monologues, podcasts, talking heads) are a single webcam shot for 30 minutes. Extract ~10 evenly-spaced sample frames first and review with Claude vision before investing in targeted extraction. If it's all talking head, skip the whole capture pipeline and note "no visual content."
- **Extract frame bursts, not single frames.** A single frame at a timestamp often catches a transition or blur. Extract ~5 frames around the target and pick the sharpest one.
- **Delete video files after extraction.** Videos are 150-300MB and re-downloadable. Keep only the optimized images in `summaries/<slug>/images/`.
- **Prefer open formats for archival video, but quality wins.** YouTube serves AV1/VP9+Opus alongside H.264+AAC. Use yt-dlp's format selector to prefer open codecs (AV1 > VP9, Opus for audio) and mux into MKV. But if open codecs aren't available (common on archive.org) or the H.264/H.265 stream is higher quality, take the better stream. Always add a `bestvideo+bestaudio` fallback to the format selector so the download never fails.
- **Embed subtitles in the archival `.mkv`.** Use `--write-auto-sub --sub-lang en --embed-subs` during the archival download so the transcript lives inside the container. This lets you delete all `transcripts/<id>.*` files after the workflow completes — everything worth keeping is in `summaries/<slug>/`.
- **archive.org needs special handling for subtitles.** yt-dlp doesn't detect archive.org subtitle files. Check the item's download page (`https://archive.org/download/<id>/`) for `.asr.srt` or `.vtt` files, download with `curl`, and embed into the MKV with `ffmpeg -i video.mkv -i subs.srt -c copy -c:s srt output.mkv`.
- **archive.org item IDs work as yt-dlp video IDs.** The archive.org identifier (e.g., `redwood-center-2026-02-11-ben-dongsung-huh`) serves as the `<id>` throughout the workflow. Use `https://archive.org/details/<id>` as the URL for yt-dlp.
- **Verify academic summaries against the source paper before copy-editing.** ASR transcripts of math-heavy talks garble technical terms ("Kaylee table" for "Cayley table," "eReps" for "irreps," "cautious rush" for "Cauchy-Schwarz"). The only reliable correction is to find the actual paper and cross-reference the claims. Do this before the Strunk & White pass — fixing factual errors after prose has been polished wastes effort.
- **GitHub Gist markdown collapses consecutive lines into one paragraph.** Metadata lines like `**Source**: ...` followed by `**Author**: ...` render as a single run-on line. Use `<br>` at the end of each line to force line breaks. Blockquotes have the same problem and also add a left bar that makes metadata look like a quotation — use plain text with `<br>` instead.
- **Don't duplicate the title in the gist description.** The gist description renders as a gray caption above the file. If it matches the H1, the title appears twice. Use a static genre label like `"Video Summary"` for the description and let the H1 carry the title.
- **Use the slug as the gist filename, not the video ID.** `frontier-operations-five-skills-tiny-teams.md` reads as a page title; `RnjgLlQTMf0.md` doesn't. The slug is already unique within the project. Write the gist-adapted markdown to `/tmp/<slug>.md` so `gh gist create` picks up the right filename.
- **Gists reject pushes with directories.** `remote: Gist does not support directories.` Copy images flat to the gist repo root instead of preserving the `images/` subfolder.
- **Rewrite image paths to absolute `gist.githubusercontent.com` raw URLs.** Relative paths don't render in gist markdown. The pattern `https://gist.githubusercontent.com/<user>/<gist-id>/raw/<filename>` resolves to the latest revision without needing a commit SHA.
- **Gists with images work fine — create first, clone-push second.** Create the gist with just the markdown via `gh gist create`, then `git clone` the gist repo, add image files at the root, rewrite the markdown image refs to absolute URLs, and push. Two-step process but reliable.
