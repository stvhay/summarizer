# Scenario: Full video workflow

## Prompt
Summarize this technical lecture for this project from its video URL. Make the result thorough enough to replace watching the video.

## Expected weak baseline
Without a project-local skill, the agent may produce an ad hoc text summary while skipping project requirements such as source-specific transcript retrieval, factual review, visual capture, archival video, and cleanup.

## Expected with skill
The agent loads the canonical workflow from `CLAUDE.md`, follows all applicable steps in order, and creates the required summary and archive without changing unrelated local artifacts.

## Assertions
- Read `CLAUDE.md` before processing the video.
- Follow its source-specific transcript path and full workflow.
- Apply factual and visual review when applicable.
- Verify the archive, then remove only the requested video's intermediate transcript artifacts.
- Do not copy the canonical workflow into the skill or alter unrelated files.
