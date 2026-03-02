---
name: writing-plans
description: Use when you have a spec or requirements for a multi-step task, before touching code
---

# Writing Plans

## Overview

Write implementation plans that are directly executable as subagent prompts. Each plan is 2-3 tasks, each task self-contained with all context needed. The plan IS the prompt — no transformation step required.

Assume the implementing engineer has zero context for our codebase. Document everything: files to touch, code, testing, relevant docs. DRY. YAGNI. TDD. Frequent commits.

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Context:** This should be run in a dedicated worktree (created by brainstorming skill).

**Save plans to:** `docs/plans/YYYY-MM-DD-<feature-name>.md`

## Plan Sizing

**Each plan: 2-3 tasks.** Each task should fit comfortably in a fresh subagent context (~50% of context window). This means:

- A task includes ALL context needed — no "see Task 1" references
- Each task is directly pasteable as a subagent prompt
- Task 3 gets the same quality execution as Task 1 (fresh context)

**Larger features = multiple plans, not one large plan.** If a feature needs 8 tasks, that's 3-4 plans. Each plan has its own acceptance criteria and can be verified independently. Note dependencies between plans where they exist.

## Task Granularity

**Each step within a task is one action:**
- "Write the failing test" - step
- "Run it to make sure it fails" - step
- "Implement the minimal code to make the test pass" - step
- "Run the tests and make sure they pass" - step
- "Commit" - step

## Plan Document Header

**Every plan MUST start with this header:**

```markdown
# [Feature Name] Implementation Plan

> **For Claude:** Execute this plan using subagent-driven-development (same session) or executing-plans (separate session / teammate).

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

**Acceptance Criteria — what must be TRUE when this plan is done:**
- [ ] [Specific verifiable condition, maps to a test]
- [ ] [Another condition]
- [ ] [Integration/behavioral condition]

**Dependencies:** [Other plans that must complete first, or "None"]

---
```

## Task Structure

Each task must be self-contained — a subagent receiving only this task text has everything needed to implement it.

```markdown
### Task N: [Component Name]

**Context:** [What this task builds, where it fits in the system, any relevant architectural decisions. Include enough that a fresh subagent understands the landscape without reading other tasks.]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

**Depends on:** [Task M, or "Independent"]

**Step 1: Write the failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

**Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/path/test.py::test_name -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
```

## Parallel vs. Sequential

Mark each task's dependencies explicitly. Independent tasks can be dispatched to subagents in parallel. Dependent tasks run sequentially.

```markdown
### Task 1: Data model          [Independent]
### Task 2: API endpoint        [Independent]
### Task 3: Integration tests   [Depends on: Task 1, Task 2]
```

Tasks 1 and 2 run in parallel. Task 3 waits for both.

## Remember
- Exact file paths always
- Complete code in plan (not "add validation")
- Exact commands with expected output
- Each task self-contained with full context
- 2-3 tasks per plan, break larger features into multiple plans
- Mark dependencies between tasks (and between plans)
- Acceptance criteria = what must be TRUE = the tests
- DRY, YAGNI, TDD, frequent commits

## Execution Handoff

After saving the plan, offer execution choice:

**"Plan complete and saved to `docs/plans/<filename>.md`. Execution options:**

**1. Subagent-Driven (this session)** - I orchestrate fresh subagents per task, independent tasks run in parallel, review between tasks

**2. Agent Team** - Spawn a teammate to execute the plan autonomously, reports back when done

**3. Separate Session** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?"**

**If Subagent-Driven chosen:**
- **REQUIRED SUB-SKILL:** Use subagent-driven-development
- Stay in this session
- Fresh subagent per task + code review

**If Agent Team chosen:**
- Spawn teammate using Task tool with `team_name`
- Teammate uses executing-plans to work through the plan
- Reports back on completion

**If Separate Session chosen:**
- Guide them to open new session in worktree
- **REQUIRED SUB-SKILL:** New session uses executing-plans
