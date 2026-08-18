# Scenario: Multipart summary navigation

## Prompt
You have already read `CLAUDE.md` and both full transcripts. Summarize two related conference recordings, each containing several sessions. Publish both as separate documents with clear navigation while keeping the summaries visually and structurally consistent. Before drafting, state the required document structure and navigation rules.

## Expected weak baseline
The agent may omit a contents list, link only to video timestamps instead of document sections, rely on fragile auto-generated heading fragments, or use official session titles in one summary and editorial thesis titles in the other.

## Expected with skill
Each multipart summary uses the same title and major-part naming pattern. It includes a contents list whose labels match the corresponding major-part headings and whose internal links navigate to stable section anchors; video timestamps remain separate links to source playback.

## Assertions
- Related summaries use one consistent document-title pattern and one consistent basis for major-part titles.
- Every multipart summary includes a contents list linking to each major part in the document.
- Contents labels match corresponding major-part titles.
- Internal section links and source-video timestamp links remain distinct.
- Use stable explicit anchors when generated heading fragments would be fragile.
- Do not force a contents list onto a short single-part summary.
