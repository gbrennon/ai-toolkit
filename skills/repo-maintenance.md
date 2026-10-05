---
name: repo-maintenance
description: Orchestrate repository work through a pull-request review loop
---

# Repo Maintenance

This skill orchestrates branch, quality, review, and merge policy for repository work.
Use `pr-interaction` for forge-specific pull-request operations.

## Overview

Use this skill for repository maintenance tasks that must finish through an open
pull request. Continue until the pull request is approved, every suggestion is
triaged, and all merge preconditions are verified.

The workflow is autonomous for routine branch creation, commits, pushes, pull
requests, review comments, and issue tracking. Never push or merge locally into
the default branch.

## Guardrails

- Work on a conventional feature branch, never the default branch.
- Use Conventional Commits for every committed change.
- Stage explicit paths and exclude session artifacts, credentials, and generated state.
- Never ignore a quality-tool finding on a modified file.
- Never merge without a fresh approval review.
- Never merge when CI is failing, pending, unavailable, or missing.
- Use the repository's default merge strategy through the forge.

## Workflow

```text
prepare branch
  -> synchronize with default branch
  -> open or update pull request
  -> wait for current-head review
  -> read and triage every review item
  -> fix blocking and in-scope items
  -> re-run quality checks and push
  -> repeat review loop
  -> verify merge preconditions
  -> merge through the forge
  -> track post-merge workflows
```

## Prerequisites

Use `pr-interaction` before any forge operation. It selects the forge CLI from
the repository remote, verifies its installed command surface, and owns pull-request
queries, comments, issue triage, status checks, and merge commands.

Know the task scope before coding. If the work comes from an issue, read its body
and comments first. State the PR's scope, exclusions, and validation in its description.

## Step 1 — Reach the loop entry

Work on a feature branch. Before opening or updating a pull request, pass this
synchronization gate:

```bash
git status --porcelain
git fetch origin
DEFAULT_BRANCH="$(
  git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null || printf 'origin/main'
)"
git merge-base --is-ancestor "$DEFAULT_BRANCH" HEAD || git rebase "$DEFAULT_BRANCH"
git status --porcelain
git log --oneline "$DEFAULT_BRANCH"..HEAD
git branch --show-current
git worktree list
```

The working tree must be clean before and after synchronization. The feature
branch must contain the latest default-branch commits. If the default branch
advances while the PR is open, repeat this gate, rerun relevant checks, and push
the updated branch before continuing.

Use `pr-interaction` to search for an existing PR. If none exists, push the
feature branch and open one against the default branch. Include motivation,
scope, changes, validation, out-of-scope follow-ups, and review notes.

## Step 2 — Read the review

After opening or updating the PR, start the installed review hook:

```bash
agent-hook-pr-review <PR-URL | owner/repo/number> --listen
```

The hook captures the current PR head before polling, ignores reviews for older
commits, and uses capped incremental backoff:
`30s`, `60s`, `120s`, `240s`, then `300s`.

When it reports a review, use `pr-interaction` to fetch the complete review and
verify that its review commit matches the current PR head. A PR comment count is
not a review verdict.

## Step 3 — Triage review items

Read every finding and suggestion. Verify uncertain findings before changing code.
Classify each item by correctness, scope, and risk:

| Review item | Action |
|---|---|
| Blocking finding or requested change | Fix it on this PR branch. |
| Correct, cheap, in-scope suggestion | Apply it on this PR branch. |
| Valuable, large, or out-of-scope suggestion | Create a tracking issue. |
| Incorrect, harmful, duplicate, or irrelevant suggestion | Dismiss it with a reason. |

An approved verdict does not eliminate suggestions. Use `pr-interaction` to post
`create issue` or `dismiss` commands, then verify their outcomes in the PR and
issue list. Do not create duplicate issues when falling back to direct issue creation.

## Step 4 — Fix and re-loop

Apply blocking fixes and justified in-scope suggestions. Write tests first for
behavior changes. Run the relevant quality checks, then the full project gate.
Commit focused changes, repeat the synchronization gate, and push the feature
branch. A new review is required after every pushed change.

Continue until the review is approved, every suggestion is triaged, and the
remote PR head contains the verified changes.

## Step 5 — Merge through the forge

Merge only when all of these conditions hold:

1. A fresh review for the current head has verdict `Approve`.
2. Every finding is resolved or explicitly justified.
3. Every suggestion is applied, dismissed with a reason, or linked to a tracking issue.
4. Every configured CI check, workflow, and action is green.
5. The PR branch is synchronized with the latest default branch.

Before merging, inspect the selected forge CLI:

```bash
"$FORGE_CLI" --help
"$FORGE_CLI" pr --help
```

Use the merge command and branch-deletion flag documented there. Do not assume
flags are portable between forge CLIs. Forge-level `mergeable` is not permission
to merge when CI is missing or unverified.

## Step 6 — Track post-merge workflows

After merging, use `pr-interaction` to track workflows for the merge commit until
each reaches a terminal state. If an initial workflow fails, perform two additional
rerun attempts and wait for each attempt to finish.

If all three attempts fail, inspect logs and status details, record the likely
cause, and create a follow-up issue whose next task implements the fix. Do not
claim the maintenance loop is complete while the pipeline remains unhealthy.

After the forge confirms the PR is merged, remove its worktree from a different
working directory and prune stale worktree metadata. Never remove the worktree
that contains the current session.
