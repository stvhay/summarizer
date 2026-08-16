---
name: video-summarization
description: Use when summarizing and archiving video or lecture material for this project, including a URL, recording, local file, or unnamed new material; not for summarizing existing text.
---

# Video Summarization

1. Read [`CLAUDE.md`](../../../CLAUDE.md) completely before processing input. Treat it as the canonical workflow.
2. If no source is named, inspect `local/inbox/` before requesting input.
3. After reading the full transcript, select its dominant summary profile from `CLAUDE.md`. For mixed material, use the dominant structure and apply stronger academic/technical standards only where needed.
4. Use `local/transcripts/` for disposable intermediates, `local/summaries/<slug>/` for final artifacts, and `local/models/` for Whisper models.
5. Follow every applicable step in order; do not substitute an ad hoc text-only summary.
6. Scope every mutation to the requested video. Preserve unrelated `CLAUDE.md`, models, transcripts, summaries, and local media.
7. Remove only the current video's intermediate transcript artifacts, and only after verifying the summary and archive.
8. If required input or access is unavailable, preserve partial work and request the missing input instead of bypassing the workflow.
