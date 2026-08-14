# Scenario: Full video workflow

## Prompt
Summarize the new technical lecture material for this project. Make the result thorough enough to replace watching the video.

## Expected weak baseline
Without project-local guidance, the agent may request a URL or search arbitrary locations instead of checking the project's default inbox. It may also produce an ad hoc text summary while skipping factual review, visual capture, archival video, and cleanup.

## Expected with skill
The agent checks `local/inbox/` for the unspecified source, loads the canonical workflow from `CLAUDE.md`, follows all applicable steps in order, and writes disposable intermediates and final artifacts to the project's consolidated local workspace without changing unrelated local artifacts.

## Assertions
- When no source is specified, inspect `local/inbox/` before requesting input.
- Read `CLAUDE.md` before processing the video.
- Use `local/transcripts/` for disposable intermediates, `local/summaries/<slug>/` for the summary, archive, and images, and `local/models/` for Whisper models.
- Follow the source-specific transcript path and full workflow.
- Apply factual and visual review when applicable.
- Verify the archive, then remove only the requested video's intermediate transcript artifacts.
- Do not copy the canonical workflow into the skill or alter unrelated files.
