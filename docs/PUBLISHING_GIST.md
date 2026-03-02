# Publishing to GitHub Gist

Publish a finished summary as a GitHub Gist for easy sharing.

## Gist Display Conventions

GitHub Gist renders three prominent elements: the **filename** (as page title), the **description** (as a gray subtitle), and the **rendered markdown**. To avoid redundancy:

- **Filename**: `<slug>.md` — the human-readable slug, not the video ID. This becomes the gist's page title (e.g., `stvhay / frontier-operations-five-skills-tiny-teams.md`).
- **Description**: `"Video Summary"` — frames the genre for anyone landing on the gist. Static across all summaries.
- **Markdown H1**: The full human-readable title. This is the reader's entry point once they're in the document.

## Gist-Adapted Front Matter

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

## Process (Text-Only)

1. **Create the gist-adapted file** at `/tmp/<slug>.md` — copy the summary, replace the multi-line front matter with the format above.
2. **Create the gist**:
   ```bash
   gh gist create --public \
     -d "Video Summary" \
     "/tmp/<slug>.md"
   ```
   Use `--public` for discoverable gists or omit for secret (URL-only) gists.
3. **Clean up** — delete `/tmp/<slug>.md`.

## Process (With Images)

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

## Key Constraints

- **Gists don't support directories.** Image files must live at the repo root.
- **Use absolute raw URLs for images.** `gist.githubusercontent.com/<user>/<gist-id>/raw/<filename>` resolves to the latest revision. Relative paths won't render.
- **Create first, clone-push second.** Create the gist with just the markdown via `gh gist create`, then clone, add images, rewrite refs, and push.
- The `.mkv` archive is too large for gists. Gists are for the summary document only.
