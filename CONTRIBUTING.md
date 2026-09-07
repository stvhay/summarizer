# Contributing

Keep the agent-led workflow small. `CLAUDE.md` is canonical; agent-specific skills should point to it rather than maintain competing requirements.

## Setup

Clone the repository and follow [README.md](README.md) for Nix or Homebrew setup. Claude Code memory setup is documented in [docs/FIRST_RUN.md](docs/FIRST_RUN.md).

## Scale the process to the change

**Small fixes and documentation changes:** explain the problem, make the smallest change, run focused checks, and review the diff. No mandatory brainstorm, worktree, or separate plan.

**Multi-step or behavior-changing work:** record scope and acceptance criteria in a work item (Bead or GitHub issue), write a short plan when useful, implement with regression checks, and review before committing. Use `.pi/plans/YYYY-MM-DD-<topic>-plan.md` for new plans, including when a bundled skill shows a generic `docs/plans/` example. Leave historical local plans where they are.

Use a branch/worktree when isolation helps; do not make it a prerequisite for a typo fix. Bundled `.claude/skills/` provide optional planning, debugging, testing, writing, and review guidance. Use the applicable skill, not every skill for every change.

Verify before claiming success. Commit task-owned changes atomically. Local implementation does not imply permission to push, open a PR, merge, or delete branches. When submitting a PR, link the work item and plan if present; small fixes can explain scope and verification directly in the PR body.

## Verification

From the repository root:

```bash
bash tests/check-workflow.sh
python3 tests/check-media-prep.py
for script in scripts/verify-archive.sh tests/check-workflow.sh .envrc .envrc.d/setup.sh; do
  bash -n "$script" || exit 1
done
git diff --check
```

The offline checks require Python 3.11+, Bash, yt-dlp, ffmpeg, and ffprobe. They exercise quality-first selection, archive rejection/acceptance, preparation, subtitle conversion, provenance, embedding, capture, and resume/conflict safety using temporary synthetic media, not existing local files. Preparation tests use loopback HTTP with real yt-dlp; a fake Whisper executable checks the ASR command/output contract, not transcription quality. No Internet access or model is required. The standalone shell archive verifier checks structure, not full decoding or subtitle fidelity.

For workflow/skill edits, also review the scenarios under `.pi/skill-evals/video-summarization/scenarios/` against the canonical workflow. Those Markdown scenarios describe behavior; the shell suite does not run model evaluations. Report which checks ran and any unverified paths.

## Dependencies and documentation

- **Nix:** change `flake.nix` (`buildInputs`) for Nix dependencies. Reload the session after changes so direnv picks them up.
- **Homebrew:** maintain its setup instructions separately in `README.md`. Update `.envrc` only when the non-Nix core-tool requirement changes; `.envrc.d/setup.sh` creates workspace directories, not dependency checks.
- **Optional tools:** check prerequisites at point of use (Whisper/model for ASR, authenticated `gh` for publishing). Do not add optional tools to every environment's startup gate.
- **Usage/output changes:** update `CLAUDE.md` and `README.md`; keep entry-point skills thin.
- **Skills:** project-owned Pi guidance lives in `.pi/skills/`; bundled Claude guidance lives in `.claude/skills/`. Preserve attribution, establish a baseline scenario before behavior changes, and verify against that scenario.

## Attribution

Several skills are derived from upstream open-source projects:

- **obra/superpowers** — The following skills originate from [obra/superpowers](https://github.com/obra/superpowers). MIT License. See [LICENSE.superpowers](LICENSE.superpowers). Sync status tracked in `.claude/skills/UPSTREAM-superpowers.md`.
  - Tracked in this repo: `brainstorming`, `dispatching-parallel-agents`, `executing-plans`, `finishing-a-development-branch`, `receiving-code-review`, `requesting-code-review`, `subagent-driven-development`, `systematic-debugging`, `test-driven-development`, `using-git-worktrees`, `verification-before-completion`, `writing-plans`, `writing-skills`
  - Available locally (not committed): `using-superpowers`
- **writing-clearly-and-concisely** — Based on William Strunk Jr.'s *The Elements of Style* (1918, public domain).

If you contribute a skill derived from another source, add appropriate attribution and a license file.

## Code of Conduct

Be kind, be constructive, assume good intent.
