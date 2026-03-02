---
name: executing-plans
description: Use when you have a written implementation plan to execute in a separate session with review checkpoints
---

# Executing Plans

## Overview

Load plan, review critically, execute tasks — independent tasks in parallel, dependent tasks in sequence. Report for review between groups. Each task gets a fresh context.

**Core principle:** Fresh context per task. Independent tasks run in parallel. Dependent tasks wait. Verify acceptance criteria at the end.

**Announce at start:** "I'm using the executing-plans skill to implement this plan."

## The Process

### Step 1: Load and Review Plan
1. Read plan file
2. Review critically — identify questions or concerns
3. Note task dependencies (which are independent, which depend on others)
4. Note acceptance criteria from plan header
5. If concerns: Raise them before starting
6. If clear: Create TodoWrite and proceed

### Step 2: Group and Execute
**Group tasks by dependencies:**
- Independent tasks → same group, execute in parallel (dispatch subagents via Task tool)
- Dependent tasks → later group, execute after dependencies complete

For each task:
1. Mark as in_progress
2. Dispatch to fresh subagent with full task text (don't make subagent read plan file)
3. Follow each step exactly (plan has bite-sized steps)
4. Run verifications as specified
5. Mark as completed

### Step 3: Report
When group complete:
- Show what was implemented
- Show verification output
- Say: "Ready for feedback."

### Step 4: Continue
Based on feedback:
- Apply changes if needed
- Execute next group
- Repeat until all groups complete

### Step 5: Verify Acceptance Criteria
After all tasks complete:
- Check each acceptance criterion from the plan header
- Run the tests that verify each condition
- Report: which criteria pass, which fail

### Step 6: Complete Development
After acceptance criteria verified:
- **REQUIRED SUB-SKILL:** Use finishing-a-development-branch
- Follow that skill to verify tests, present options, execute choice

## Agent Teams

For larger efforts or autonomous execution, this skill can be run by a **teammate** rather than in a manual session:

1. Controller spawns teammate using Task tool with `team_name`
2. Teammate loads and executes the plan
3. Teammate reports progress via messages
4. Controller reviews and unblocks as needed

This replaces the old "open a new terminal session" pattern.

## When to Stop and Ask for Help

**STOP executing immediately when:**
- Hit a blocker (missing dependency, test fails, instruction unclear)
- Plan has critical gaps
- You don't understand an instruction
- Verification fails repeatedly

**Ask for clarification rather than guessing.**

## Remember
- Review plan critically first
- Group tasks by dependencies — parallelize what you can
- Each task gets fresh context (full task text, not file references)
- Follow plan steps exactly
- Don't skip verifications
- Verify acceptance criteria after all tasks complete
- Stop when blocked, don't guess
