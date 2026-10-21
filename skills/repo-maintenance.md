---
name: repo-maintenance
description: Orchestrate repository work through a pull-request review loop
---

# Repo Maintenance

This skill orchestrates branch, quality, review, and merge policy for repository work.
Use `pr-interaction` for forge-specific pull-request operations.

## Overview

Use this skill for repository maintenance tasks that must finish through an open
pull request. Continue until merge preconditions are verified, every review item
is triaged, and every post-merge follow-up reaches a terminal state.

The workflow is autonomous for routine branch creation, commits, pushes, pull
requests, review comments, issue tracking, and authorized forge merges. It never
pushes directly to or merges locally into the default branch. When the user
authorizes autonomous maintenance, it may merge a pull request through the forge
after the review policy, CI, and synchronization gates pass.

## Autonomous Scope and Notifications

Start from the user's stated scope and execute routine repository work without
requesting confirmation for each branch, commit, test, push, or review action.

- Do not ask for routine confirmation.
- Ask a question only when scope is materially missing or contradictory.
- Send notifications for the `question`, `complete`, and `error` events through
  `agent-notify`.
- Include the agent, event, cwd, tmux session, window index, and window name.
- Always notify, including the visible tmux window.
- Send the `complete` event only after the current task reaches its terminal
  outcome.
- Send error when a task or required gate reaches a failure outcome.

## Guardrails

- Work on an expressively named conventional feature branch, never the default branch.
- Dedicate one branch to one pull request and name it after the change it makes.
- Never put a number in a branch name unless it is an issue reference that
  auto-closes that issue on merge.
- Use Conventional Commits for every committed change.
- Stage explicit paths and exclude session artifacts, credentials, and generated state.
- Never ignore a quality-tool finding on a modified file.
- Require a fresh approval review only when the repository enforces required reviews.
- Never merge while a configured CI workflow is failing, pending, or unverified.
- Re-run a failing CI workflow before and after merge, then investigate repeats.
- Use the repository's default merge strategy through the forge.
- Always delete the merged branch on the remote and locally after merge.

## Workflow

```text
prepare an expressively named branch
  -> synchronize with default branch
  -> open or update pull request
  -> wait for current-head review
  -> read and triage every review item
  -> fix blocking and in-scope items
  -> re-run quality checks and push
  -> repeat review loop
  -> keep pull-request CI green, re-running failed workflows
  -> verify review policy and merge preconditions
  -> merge through the forge
  -> delete the remote and local branch
  -> track post-merge workflows and auto-opened follow-ups
```

## Prerequisites

Use `pr-interaction` before any forge operation. It selects the forge CLI from the
repository remote, verifies its installed command surface, and owns pull-request
queries, comments, issue triage, status checks, workflow reruns, and merge commands.

Know the task scope before coding. If the work comes from an issue, read its body
and comments first. State the PR's scope, exclusions, and validation in its description.

## Step 1 — Reach the loop entry

Work on an expressively named feature branch dedicated to this one pull request.
Name the branch after the change; add a number only when it is an issue reference
that auto-closes that issue on merge. Before opening or updating a pull request,
pass this synchronization gate:

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
not a review verdict. A review is not required on every repository; see Step 6.

## Step 3 — Triage review items

Read every finding and suggestion. Verify uncertain findings before changing code.
Classify each item by correctness, scope, and risk:

| Review item | Action |
|---|---|
| Blocking finding or requested change | Fix it on this PR branch. |
| Correct, cheap, in-scope suggestion | Apply it on this PR branch. |
| Valuable, large, or out-of-scope suggestion | Comment `create issue <ids>` on the PR. |
| Incorrect, harmful, duplicate, or irrelevant suggestion | Comment `dismiss <ids>` on the PR. |

When `pr-auto-reviewer` posts the review, act only in this post-review phase and
only through pull-request comment commands. The bot has no chat interface; it
understands only `create issue <ids>` and `dismiss <ids>`. Post exactly one
batched command per review, then verify the outcome in the PR and issue list.
Never manually invoke an issue-creation command and never use a direct
issue-creation fallback.

## Step 4 — Fix and re-loop

Apply blocking fixes and justified in-scope suggestions. Write tests first for
behavior changes. Run the relevant quality checks, then the full project gate.
Commit focused changes, repeat the synchronization gate, and push the feature
branch. A new review is required after every pushed change.

Continue until every review item is triaged and the remote PR head contains the
verified changes.

## Step 5 — Keep pull-request CI green

Use `pr-interaction` to read the workflow runs for the current PR head. Apply this
rerun policy to any failing workflow, before and after merge:

- Re-run the failed workflow and wait for the attempt to reach a terminal state.
- Perform at most two additional rerun attempts when a flake is plausible.
- Stop rerunning once the workflow passes.
- When it keeps failing, inspect logs and status details and investigate the cause
  instead of rerunning again.
- Record the likely cause and open a tracking issue when the failure is real.

A green run must match the current PR head. Do not advance to merge while a
configured workflow is failing, pending, or unverified.

## Step 6 — Merge through the forge

First establish whether the repository requires an approving review. Use
`pr-interaction` to read the branch-protection or merge policy; never infer it from
forge-level `mergeable` alone. Then merge only when all of these hold:

1. The review policy is satisfied: when the repository requires review, a fresh
   review for the current head has verdict `Approve`; otherwise approval is not needed.
2. Every finding is resolved or explicitly justified.
3. Every suggestion is applied, dismissed, or tracked with `create issue`.
4. Every configured CI check, workflow, and action is green per Step 5.
5. When no CI workflows are configured, local quality gates satisfy this condition.
6. The PR branch is synchronized with the latest default branch.

Before merging, inspect the selected forge CLI:

```bash
"$FORGE_CLI" --help
"$FORGE_CLI" pr --help
```

Use the merge command and branch-deletion flag documented there. Do not assume
flags are portable between forge CLIs. Forge-level `mergeable` is not permission to
merge when configured CI is missing or unverified. After the forge confirms the
merge, always delete the remote branch with the documented flag and delete the
local branch; neither deletion is optional.

## Step 7 — Track post-merge work

After merging, use `pr-interaction` to track workflows for the merge commit until
each reaches a terminal state. Apply the Step 5 rerun-and-investigate policy to any
post-merge failure. Do not claim the loop is complete while the pipeline remains
unhealthy.

Always complete auto-opened post-merge work. Some repositories automatically open a
follow-up pull request or issue after merge, such as a changelog update. Pick up
each such item and run it through this same loop until it reaches a terminal state.

After the forge confirms the PR is merged, remove its worktree from a different
working directory and prune stale worktree metadata. Never remove the worktree
that contains the current session.
