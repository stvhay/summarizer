# Local Video Workspace Implementation Plan

**Issue:** summarizer-aj3 — Consolidate local video workspace
**Design:** Bead `summarizer-aj3`
**Date:** 2026-08-14
**Branch:** main

**Goal:** Consolidate disposable input, intermediates, outputs, and Whisper models under ignored `local/` paths without changing existing data.

**Architecture:** Keep `local/projects/` untouched. Use direct paths `local/inbox/`, `local/transcripts/`, `local/summaries/`, and `local/models/`; same-filesystem directory renames preserve existing data.

**Acceptance Criteria:**
- [ ] Skill and baseline scenario direct unspecified video material to `local/inbox/` and outputs to consolidated paths.
- [ ] Canonical workflow, setup, README, publishing guide, and ignore rules use consolidated paths.
- [ ] Root `transcripts/`, `summaries/`, and `models/` move to collision-free destinations with matching directory inodes and manifests.
- [ ] Focused behavior/static checks pass.

**Verification Commands:**
```bash
rg -n 'local/(inbox|transcripts|summaries|models)' .pi/skills/video-summarization/SKILL.md .pi/skill-evals/video-summarization/scenarios/full-video-workflow.md CLAUDE.md README.md docs/PUBLISHING_GIST.md .envrc.d/setup.sh .gitignore
! git grep -nE '(^|["`[:space:]])(transcripts|summaries|models)/' -- CLAUDE.md README.md docs/PUBLISHING_GIST.md .envrc.d/setup.sh .gitignore
~/.pi/agent/bin/agnt context-health --strict
```

---

### Task 1: Establish behavior baseline

Update `.pi/skill-evals/video-summarization/scenarios/full-video-workflow.md` first so unspecified new video material must be discovered in `local/inbox/` and workflow artifacts use consolidated paths. Confirm current skill fails those assertions.

### Task 2: Update tracked workflow paths

Make minimum edits to `.pi/skills/video-summarization/SKILL.md`, `CLAUDE.md`, `.envrc.d/setup.sh`, `.gitignore`, `README.md`, and `docs/PUBLISHING_GIST.md`. Preserve workflow and unrelated guidance.

### Task 3: Move ignored workspace data

Before mutation, require all three source directories, absent destinations, unchanged source metadata manifests, and same source/destination filesystem. Rename each source under `local/`, create empty `local/inbox/`, then verify destination inodes and manifests match pre-move evidence. Stop on any failed gate; do not delete or overwrite.

### Task 4: Verify and close

Run focused static checks, behavior evals, context health, diff review, and data checks. Commit tracked task-owned changes, then run direct closeout.
