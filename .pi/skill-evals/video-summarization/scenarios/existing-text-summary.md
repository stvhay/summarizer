# Scenario: Existing text summary

## Prompt
Summarize this existing transcript excerpt into a concise memo: “The speaker compares two indexing strategies and recommends the simpler one for small datasets.” Do not retrieve or process a video.

## Expected weak baseline
A broad summarization trigger may load the video workflow even though the request supplies text and explicitly excludes video processing.

## Expected with skill
The skill does not trigger. The agent summarizes the supplied text without reading `CLAUDE.md` or creating video workflow artifacts.

## Assertions
- Do not load the `video-summarization` skill.
- Do not read `CLAUDE.md`.
- Do not retrieve, transcribe, capture, archive, or clean up video artifacts.
