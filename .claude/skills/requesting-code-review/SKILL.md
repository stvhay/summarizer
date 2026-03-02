---
name: requesting-code-review
description: Use when completing tasks, implementing major features, or before merging to verify work meets requirements
---

# Requesting Code Review

Dispatch code-reviewer subagent to catch issues before they cascade.

**Core principle:** Review early, review often.

## When to Request Review

**Mandatory:**
- After each task in subagent-driven development
- After completing major feature
- Before merge to main

**Optional but valuable:**
- When stuck (fresh perspective)
- Before refactoring (baseline check)
- After fixing complex bug

## How to Request

**1. Detect context:**

Determine if a PR exists for the current branch and whether you are the author:

```bash
# Get PR number (empty if no PR exists)
PR_NUMBER=$(gh pr view --json number --jq '.number' 2>/dev/null || echo "")

# If PR exists, check authorship
if [ -n "$PR_NUMBER" ]; then
  PR_AUTHOR=$(gh pr view --json author --jq '.author.login')
  CURRENT_USER=$(gh api user --jq '.login')
  IS_AUTHOR=$( [ "$PR_AUTHOR" = "$CURRENT_USER" ] && echo "true" || echo "false" )
fi
```

If no PR exists, the review runs locally only (existing behavior).

**2. Get git SHAs:**
```bash
BASE_SHA=$(git rev-parse HEAD~1)  # or origin/main
HEAD_SHA=$(git rev-parse HEAD)
```

**3. Dispatch code-reviewer subagent:**

Use Task tool with code-reviewer type, fill template at `code-reviewer.md`

**Placeholders:**
- `{WHAT_WAS_IMPLEMENTED}` - What you just built
- `{PLAN_OR_REQUIREMENTS}` - What it should do
- `{BASE_SHA}` - Starting commit
- `{HEAD_SHA}` - Ending commit
- `{DESCRIPTION}` - Brief summary
- `{PR_NUMBER}` - PR number (empty for local-only review)
- `{IS_AUTHOR}` - `true` if current user authored the PR, `false` otherwise

**4. Act on feedback:**
- Fix Critical issues immediately
- Fix Important issues before proceeding
- Note Minor issues for later
- Push back if reviewer is wrong (with reasoning)

## Example: Local Review (no PR)

```
[Just completed Task 2: Add verification function]

You: Let me request code review before proceeding.

PR_NUMBER=""  # No PR exists yet
BASE_SHA=$(git log --oneline | grep "Task 1" | head -1 | awk '{print $1}')
HEAD_SHA=$(git rev-parse HEAD)

[Dispatch code-reviewer subagent with PR_NUMBER="" IS_AUTHOR=""]

[Subagent returns review locally]
You: [Fix issues, continue to Task 3]
```

## Example: PR Review (self-authored)

```
[PR #5 is open, you are the author]

PR_NUMBER=5, IS_AUTHOR=true

[Dispatch code-reviewer subagent]
[Subagent posts structured comment on PR #5]
[Clean review: comment signals LGTM — no --approve attempted]
[Issues found: comment lists them — no --request-changes attempted]
```

## Example: PR Review (external)

```
[PR #12 from a contributor, you are not the author]

PR_NUMBER=12, IS_AUTHOR=false

[Dispatch code-reviewer subagent]
[Subagent posts structured comment on PR #12]
[Clean review: gh pr review 12 --approve]
[Issues found: gh pr review 12 --request-changes]
```

## Integration with Workflows

**Subagent-Driven Development:**
- Review after EACH task
- Catch issues before they compound
- Fix before moving to next task

**Executing Plans:**
- Review after each batch (3 tasks)
- Get feedback, apply, continue

**Ad-Hoc Development:**
- Review before merge
- Review when stuck

## Red Flags

**Never:**
- Skip review because "it's simple"
- Ignore Critical issues
- Proceed with unfixed Important issues
- Argue with valid technical feedback

**If reviewer wrong:**
- Push back with technical reasoning
- Show code/tests that prove it works
- Request clarification

See template at: requesting-code-review/code-reviewer.md
