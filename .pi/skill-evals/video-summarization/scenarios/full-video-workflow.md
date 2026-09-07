# Scenario: Full video workflow

## Prompt
Summarize the new technical lecture material for this project. Make the result thorough enough to replace watching the video.

## Expected weak baseline
Without project-local guidance, the agent may request a URL instead of checking the inbox or skip required review steps. The earlier workflow downloaded video twice, prioritized any AV1 over higher-quality alternatives, and deleted transcripts while treating embedded subtitles as optional. The Pi skill also carried navigation and preservation rules absent from the canonical workflow.

## Expected with skill
The agent checks `local/inbox/` for the unspecified source, loads the canonical workflow from `CLAUDE.md`, follows all applicable steps in order, and writes disposable intermediates and final artifacts to the project's consolidated local workspace without changing unrelated local artifacts.

## Assertions
- When no source is specified, inspect `local/inbox/` before requesting input.
- Read `CLAUDE.md` before processing the video.
- Use `local/transcripts/` for intermediates, `local/summaries/<slug>/` for the summary, archive, provenance, and images, and `local/models/` for Whisper models.
- Acquire the archive once using the shared yt-dlp config or local remux; reuse it for ASR and visual extraction.
- Keep Nix and Homebrew dependency lists separate; check optional tools when their branch is needed.
- Follow the source-specific transcript path and full workflow.
- Apply factual and visual review when applicable.
- Preserve metadata, readable transcript, and original source/ASR subtitles beside the summary before cleanup.
- Run the archive verifier with subtitles required by default; retain original archive until any replacement candidate verifies.
- Compare preserved copies, review summary/links, then remove only explicit disposable paths from this run. Failure preserves partial work.
- Follow canonical multipart navigation rules even without the Pi skill loaded.
- Do not copy the canonical workflow into the skill or alter unrelated files.
