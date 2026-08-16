# Scenario: Genre-aware interview summary

## Prompt
You have read the full transcript and verified metadata for an hour-long current-affairs video interview. Before drafting and publishing it, state the summary structure, timestamp placement, visual-selection rule, and final review sequence you will use. The result must be thorough enough to replace watching the video. It is not an academic lecture.

## Expected weak baseline
The agent may apply one generic summary template to every video: retell the interview chronologically, repeat an executive summary in the conclusion, collect timestamps in a detached chapter list, include decorative talking-head frames, or apply academic citation work that adds little value. Editing may tighten sentences before the structure and claims are stable.

## Expected with skill
The agent selects the interview/news profile. It leads with one compact bottom line, organizes detail around the conversation's main claims and tensions, places selective timestamps in relevant section headings, preserves attribution and concrete examples, and omits visuals that add no information. It reserves lecture-style exposition and primary-paper verification for academic or technical material, then runs one final clarity pass after structural and factual review.

## Assertions
- Classify the video's primary profile after reading the full transcript; apply higher rigor only where mixed material needs it.
- For interview/news material, use one compact top-level synthesis and do not repeat it at the end.
- Keep each synthesis thesis visually distinct from its explanation.
- Put selective timestamp links in corresponding major section headings unless the user requests a separate chapter guide; keep linked headings chronological after editing.
- Preserve attribution, disagreements, uncertainty, disclosures, recommendations, and concrete examples.
- Use only verified verbatim quotations; paraphrase the rest.
- Omit talking heads, studio shots, and other decorative frames; include only visuals that convey information absent from the conversation.
- Do not force the interview template onto academic or technical lectures; prioritize definitions, methods, evidence, result status, limitations, primary sources, and explanatory visuals there.
- Perform structural and factual review before the final clarity-and-concision pass.
