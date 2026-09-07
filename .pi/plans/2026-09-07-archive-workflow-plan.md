# Archive Workflow Implementation Plan

**Issue:** summarizer-ubp
**Design:** Approved architecture review in current session
**Date:** 2026-09-07
**Branch:** main

**Goal:** Acquire video once, preserve provenance before cleanup, and reduce workflow drift.

**Architecture:** Keep agent-led content work. Use native yt-dlp configuration for quality-first downloads and one read-only Bash/ffprobe archive check. No cleanup automation, new dependencies, or changes to existing local media. Keep Nix and Homebrew dependency lists independent; document optional prerequisites at point of use.

## Tasks

1. Add `tests/check-workflow.sh` with offline yt-dlp format fixtures and tiny ffmpeg media fixtures. Observe failure before implementation.
2. Add `scripts/archive.conf` and `scripts/verify-archive.sh`. Update `CLAUDE.md`, thin `.pi/skills/video-summarization/SKILL.md`, full-workflow scenario, `README.md`, `CONTRIBUTING.md`, publishing guide, and PR template. Preserve metadata, readable transcript, and source/ASR subtitles; remux once; verify before exact-file cleanup; use `.pi/plans/` for new plans.
3. Run offline checks, shell syntax and diff checks; review implementation, commit task-owned files, and close Bead through direct-closeout. No push/PR or unrelated cleanup.

## Acceptance

- Format selection prioritizes quality over codec, supports combined streams, and prefers open codecs on ties.
- Archive check rejects unreadable/non-Matroska files and missing video/audio/subtitles; explicit subtitle-free exception required.
- ASR and visual extraction reuse archive; subtitle embedding retains original until replacement verifies.
- Provenance survives cleanup; no blanket transcript glob deletion.
- Shared navigation/safety requirements live in canonical workflow, not agent-specific skill.
- Small contributions need no mandatory brainstorm/plan ceremony; Nix/Homebrew remain separate.

## Verification

```bash
bash tests/check-workflow.sh
for script in scripts/verify-archive.sh tests/check-workflow.sh .envrc .envrc.d/setup.sh; do
  bash -n "$script" || exit 1
done
git diff --check
```

Offline tests use temporary synthetic media only. External downloads, actual summarization, and Homebrew/Nix environment rebuilds are not part of verification.
