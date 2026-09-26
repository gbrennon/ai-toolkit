---
name: repo-maintenance
description: Use when contributing to or maintaining a repo through the full commit → open PR → auto-review → act on feedback → loop cycle, especially when an automated reviewer posts findings, suggestions, and an approve/request-changes verdict and you must decide what to fix now versus defer to a future issue based on task scope.
---

# Repo Maintenance

## Overview

Drive a change from working tree to merged PR through an automated review loop. An
auto-reviewer posts **findings**, **suggestions**, and a verdict (**Approve** or
**Request changes**). Your job is to act on that feedback correctly and re-loop until
the PR is approved.

**Core principle:** Blocking feedback is fixed in this PR; non-blocking suggestions are
triaged by *task scope* — in-scope cheap suggestions get applied now, out-of-scope
suggestions get deferred to issues via the reviewer's `create issue` command. Scope, not
convenience, decides.

**Announce at start:** "I'm using the repo-maintenance skill to drive this change through review."

## The Loop

```dot
digraph loop {
    "Branch + implement + test" [shape=box];
    "Commit + open PR" [shape=box];
    "Auto-review runs" [shape=box];
    "Verdict?" [shape=diamond];
    "Triage each item by scope" [shape=box];
    "Fix blocking + in-scope; defer out-of-scope to issues" [shape=box];
    "Push fixes" [shape=box];
    "Finish branch (merge/PR)" [shape=box];

    "Branch + implement + test" -> "Commit + open PR";
    "Commit + open PR" -> "Auto-review runs";
    "Auto-review runs" -> "Verdict?";
    "Verdict?" -> "Triage each item by scope" [label="request changes"];
    "Triage each item by scope" -> "Fix blocking + in-scope; defer out-of-scope to issues";
    "Fix blocking + in-scope; defer out-of-scope to issues" -> "Push fixes";
    "Push fixes" -> "Auto-review runs" [label="re-review"];
    "Verdict?" -> "Finish branch (merge/PR)" [label="approve"];
}
```

## Prerequisites

Detect the forge once — every forge operation below auto-detects from the remote URL:

```bash
uv run forge-detect
```

Know the **task scope** before you start: the originating issue, spec, or ticket. If
there is no written scope, state in one sentence what this PR is and is not about. You
cannot triage suggestions without it.

## Step 1 — Branch, implement, commit

- Create a branch with the correct prefix. **REQUIRED SUB-SKILL:** use `conventional-branch`.
- Implement the change. Write tests first where the work is a feature or bugfix
  (**REQUIRED SUB-SKILL:** `test-driven-development` / `bug-fix-tdd`).
- Commit per file with Conventional Commits. **REQUIRED SUB-SKILL:** use `conventional-commit`.
- Verify before claiming done. **REQUIRED SUB-SKILL:** use `verification-before-completion`.

## Step 2 — Open the PR

Push the branch and open the PR against the base branch. Write a PR body that states the
**scope** explicitly (link the originating issue). The scope statement is what you and
the reviewer will measure every suggestion against.

## Step 3 — Read the review

When the auto-reviewer finishes, fetch its output rather than eyeballing the web UI:

```bash
uv run fetch-pr-review <PR-URL | owner/repo/number>
```

Read the whole review: the verdict, every **finding**, and every **suggestion** with its
id. Do not react yet — triage first.

If any finding's correctness is in doubt, **REQUIRED SUB-SKILL:** use `verify-pr-feedback`
to classify it real / wrong / partial before acting. Do not blindly implement.
**REQUIRED SUB-SKILL:** use `receiving-code-review` — verify before implementing, push
back with reasoning when a finding is wrong.

## Step 4 — Triage each item by scope

Classify **every** review item with this table. "In scope" means the item is about code
this PR changed *and* stays within the PR's stated goal. Out of scope = unrelated code,
goal expansion, or a broad refactor the task never asked for.

| Item | Blocking? | In scope? | Action |
|------|-----------|-----------|--------|
| Requested change / verdict blocker | Yes | — | **Fix in this PR.** Mandatory before merge. |
| Finding (bug, correctness, security) | Treat as blocking | Yes | Fix in this PR. |
| Finding on code you didn't touch | No | No | Defer to an issue; note it in the PR. |
| Suggestion — cheap & in scope | No | Yes | Apply in this PR. |
| Suggestion — large/risky but in scope | No | Yes | Defer to an issue with rationale; keep PR focused. |
| Suggestion — out of scope | No | No | Defer to an issue via `create issue`. |

Rule of thumb: **a suggestion never expands the PR's scope.** If applying it would grow
the diff beyond the task, it becomes a future issue instead.

## Step 5 — Defer suggestions to issues

Suggestions are non-blocking. For every suggestion you decided to defer, hand its id to
the reviewer's issue-creation command by commenting on the PR. Batch all deferred ids
into **one** comment:

```
create issue <suggestion_id_1> , <suggestion_id_2> , <suggestion_id_3>
```

- Include exactly the ids you are deferring — one command, ids separated by ` , ` (a
  space on each side of the comma), however many suggestions there are.
- Do **not** list a suggestion here that you are applying in this PR.
- After the reviewer opens the issues, the deferral is done; the suggestion is no longer
  your concern for this PR.

If your forge's reviewer does not support that command, create the issues directly and
reference them back in the PR:

```bash
uv run forge-issue create <owner/repo> "<title>" --label <role>   # body from stdin
```

For breaking a larger deferred suggestion into proper vertical slices, use `to-issues`.

## Step 6 — Fix, push, re-loop

- Apply blocking fixes and in-scope suggestions. Commit them per file (`conventional-commit`).
- Push. This retriggers the auto-review.
- Go back to **Step 3**. Repeat until the verdict is **Approve**.

Each loop should shrink the finding list. If new findings appear on code you just touched,
they are in scope — fix them.

## Step 7 — Finish

When the verdict is **Approve** and tests pass, integrate the branch. **REQUIRED
SUB-SKILL:** use `finishing-a-development-branch` to merge / open-for-review / clean up.

Confirm every deferred suggestion has a tracking issue before you close the loop.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Applying every suggestion to make the reviewer happy | Suggestions are non-blocking. Triage by scope, not by approval-seeking. |
| Letting a suggestion balloon the PR scope | Defer it to an issue. Keep the PR to its stated goal. |
| Silently ignoring out-of-scope suggestions | Every deferred item gets an issue. "Defer" ≠ "drop." |
| One `create issue` comment per suggestion | Batch all deferred ids into a single comma-separated command. |
| Blindly implementing a finding that's wrong | Verify with `verify-pr-feedback`; push back with `receiving-code-review`. |
| Merging with unresolved requested changes | Blocking items must be fixed before finishing. |
| Skipping re-review after pushing fixes | The loop isn't done until the reviewer re-runs and approves. |

## Red Flags — STOP

- "I'll just apply this out-of-scope suggestion since it's small" → scope decides, not size. Defer it.
- "I'll drop this suggestion, it's minor" → create an issue instead.
- "The reviewer requested changes but I think it's fine, I'll merge" → fix or push back with evidence; never merge over a blocker.
- "I fixed things locally, PR is basically approved" → not until the auto-review re-runs and approves.
