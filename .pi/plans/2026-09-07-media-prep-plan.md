# Thin media preparation design-plan

**Issue:** summarizer-8ku
**Design:** Bead approval/notes
**Date:** 2026-09-07
**Branch:** main

## Goal and boundary

One Python 3 stdlib CLI, `scripts/media-prep.py`, with `prepare`, `capture`, and read-only `verify`. Reuse `scripts/archive.conf` and `scripts/verify-archive.sh`. No application framework, model changes, existing-media migration, automatic cleanup, publication, or claims of measured speed/quality improvement.

Source-owned summary directory and transcript reservation record prevent accidental adoption of existing files. Persist exact source identity, preparation options and hashes of completed artifacts. Check hashes before resuming; preserve incomplete/unrecorded files and fail closed. Serialize same-source mutations. Keep command logs local and compact JSON on stdout. Verify subtitle cues and A/V packet hashes/timing before replacing a newly acquired archive; retain pre-subtitle archive. Verification must not write logs/state or mark human content review complete.

Local input: stable content-based ID, ffprobe metadata, copy-remux all streams, choose English text subtitles or require explicit track when ambiguous. Explicit sidecars support SRT/VTT/JSON3. Online input: yt-dlp metadata then shared archival config; source subtitles before ASR. For archive.org missing detected subtitles, stop for agent's direct-sidecar check instead of silently using ASR. ASR needs available whisper-cli/model and records warnings. JSON3 and SRT become shared timed cues for transcript and embedding; VTT uses ffmpeg's parser. Capture default 12 overview frames or five-frame bursts at requested times; selection/optimization stays human/agent-owned.

## Files and sequence

1. Add `tests/check-media-prep.py`: synthetic local A/V, sidecars and embedded subtitles; assert missing helper first. Extend checks with each behavior before implementation.
2. Add `scripts/media-prep.py`: local prep/conversion/provenance/verified embedding, conflict/resume/read-only verification, batched capture, then online and optional ASR branches. External-service/Whisper branch contracts may use isolated fake executables; real ffmpeg/ffprobe do media work.
3. Update `README.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `flake.nix` for CLI boundary, checks and explicit Python prerequisite. Keep entry-point skills and core environment gate unchanged; request session reload after flake change.
4. Review diff and preservation boundary; fix reproduced findings, run complete checks, stage only task files, local atomic commit, direct-closeout and handoff.

## Acceptance and verification

- Offline checks prove local preparation, subtitle conversion, provenance, verified embedding, frame extraction, resume/conflict safety and read-only verification.
- No implicit cleanup/publication; originals/partial failures preserved. Logs and state are local/private.
- CLI and Python prerequisite documented; untested live network/real ASR paths explicitly reported.
- Task-owned changes committed; unrelated Beads backup/interactions untouched.

```bash
python3 tests/check-media-prep.py
bash tests/check-workflow.sh
for script in scripts/verify-archive.sh tests/check-workflow.sh .envrc .envrc.d/setup.sh; do bash -n "$script" || exit 1; done
git diff --check
git diff --cached --check
```

## Implementation evidence

- Added `scripts/media-prep.py` and `tests/check-media-prep.py`; updated README, canonical workflow, contributing checks and explicit Python dependency.
- RED: `python3 tests/check-media-prep.py` initially failed with `missing prepare/capture/verify helper`; VTT/online-source additions failed before their implementation. Fractional capture-name collision and local AAC remux tests exposed additional boundary bugs before fixes.
- GREEN: the same command passes with real local Matroska/MP4 preparation, SRT/VTT/JSON3 conversion, existing embedded-track reuse, exact provenance, changed-packet rejection, timestamped capture, no-write verification/resume, partial-file preservation, symlink/conflict refusal, real loopback yt-dlp archive/subtitle downloads, offline remote resume and fake-Whisper audio/output contract.
- Local MP4 evidence: ffmpeg shifted AAC priming from -0.064 seconds to zero and duration from 3.000 to 3.064 seconds without changing packet payloads. Acquisition comparison therefore allows container timing normalization; subtitle embedding still compares exact packet PTS/DTS/durations and payloads. This distinction is documented.
- Review: subscription Astra repository review found F-001, capture bypassing `Work.path` for dangling image symlinks. Fresh independent verifier and parent regression reproduced outside-workspace writes. Every concrete frame output now uses the existing path guard; regression passes. Private outputs: `local/reviews/summarizer-8ku/{findings.json,verified-findings.json,verifier.txt}`. No unresolved review findings.
- Manually checked all four video-summarization scenarios: source workflow/content review boundaries preserved; entry-point trigger, genre profiles and multipart navigation unchanged. No model scenario evaluation was run.
- Limits: no live YouTube/archive.org/network service testing, real ASR quality test, Nix rebuild, publishing, cleanup or existing-media changes. Loopback HTTP and fake Whisper test mechanical contracts only. Python is already available for verification; session reload requested for the flake change.
