---
title: Repository maintenance orchestrator
status: approved
date: 2026-10-01
---

# Repository Maintenance Orchestrator

## Motivation

The repository-maintenance skill describes an autonomous pull-request loop, but the
`repo-maintenance` console command is currently a placeholder: it accepts only GitHub
URLs, writes a fabricated approved status file, and does not inspect or mutate a real
pull request. Agents need a callable command that owns the repeatable forge operations
while the calling agent owns code changes.

The orchestrator will support GitHub and Forgejo-family repositories through the existing
forge detection and API modules. It will synchronize the current worktree before
push/merge operations, consume `pr-auto-reviewer` review results, handle review triage
commands, and merge automatically only after approval and green CI/CD.

## Goals

- Provide a real `repo-maintenance` command that an agent can call repeatedly.
- Detect the repository forge and use the existing forge-specific adapters.
- Discover the current PR from an explicit reference or the current branch.
- Enforce the pre-push/pre-PR synchronization gate from the repository-maintenance skill.
- Fetch and classify review verdicts, findings, suggestions, and CI/check status.
- Return deterministic machine-readable states so the calling agent knows its next action.
- Handle valuable out-of-scope suggestions and incorrect findings by posting the required
  `create issue ...` and `dismiss ...` reviewer commands.
- Merge automatically through the forge when the review is approved and all CI/CD checks
  are green, using the forge/repository default merge strategy and `--delete`.
- Preserve a local run record so repeated calls do not duplicate comments or actions.

## Non-goals

- The orchestrator will not generate or edit source code. The calling coding agent applies
  in-scope fixes and invokes the command again.
- It will not merge locally into the default branch.
- It will not force squash, rebase, or another merge strategy. The forge/repository default
  strategy is authoritative.
- It will not silently dismiss review feedback or treat an absent CI result as green.
- It will not introduce a daemon, background service, webhook server, or provider-specific
  coding-agent integration in the first implementation.

## User-facing command

The existing `repo-maintenance` console entry point remains the public interface. It will
accept an optional PR reference and options suitable for both humans and agents:

```text
repo-maintenance [PR_REFERENCE] [--json] [--once] [--no-merge]
```

- `PR_REFERENCE` accepts a full forge URL or the existing owner/repository/number form.
  When omitted, the command resolves the current branch and repository remote.
- `--json` emits one stable JSON result object and suppresses prose status output. This is
  the primary agent integration contract.
- `--once` performs one state evaluation/action pass and exits instead of polling.
- `--no-merge` evaluates and handles review actions but never invokes the merge operation.
  This is useful for dry-run or policy-controlled callers.

The default mode is autonomous polling with a bounded interval and no unbounded retry. The
command exits after a terminal state, an actionable agent state, or an operational error.
Configuration is provided through command options or environment variables; credentials
remain owned by `gh`, `fj`, `FORGEJO_TOKEN`, or `FJ_TOKEN` as supported by the existing
adapters.

## State contract

Every run returns a result with at least:

```json
{
  "state": "waiting_for_review",
  "pr": {"host": "codeberg.org", "owner": "owner", "repo": "repo", "number": 42},
  "branch": "feat/example",
  "default_branch": "origin/main",
  "review": {"verdict": "pending", "findings": [], "suggestions": []},
  "checks": {"state": "pending", "failed": [], "pending": []},
  "actions": [],
  "next_action": "wait_for_review"
}
```

Required terminal/action states:

- `changes_required`: in-scope findings require the calling agent to edit code and rerun
  the command.
- `review_actions_required`: review items need explicit issue-creation or dismissal
  comments and cannot be resolved automatically from the available evidence.
- `waiting_for_review`: no approved review exists yet.
- `waiting_for_ci`: review is approved but one or more required checks are pending.
- `blocked`: a failed check, synchronization failure, invalid review state, or missing
  required credential/tool prevents progress.
- `merged`: the forge confirmed the PR merge and branch deletion.
- `closed`: the referenced PR is closed without being merged.

The process exit status is `0` for `merged`, `waiting_for_review`, and `waiting_for_ci`,
so polling is not mistaken for an operational failure. It is nonzero for `changes_required`,
`review_actions_required`, `blocked`, `closed`, and tool/API errors. The JSON payload is
always the source of detailed next-action information.

## Loop and data flow

1. **Resolve repository context.** Read the remote, detect the forge, resolve the default
   branch from `refs/remotes/origin/HEAD` with `origin/main` fallback, and identify the
   current branch/worktree. Reject detached or wrong worktrees for mutating actions.
2. **Synchronize before mutation.** Require a clean tree, fetch `origin`, verify the default
   branch is an ancestor, and rebase when it is not. Re-check cleanliness and branch/worktree
   identity after rebase. A conflict produces `blocked` with the exact recovery command;
   it never pushes or merges.
3. **Resolve the PR.** Use the explicit reference when supplied. Otherwise locate the open
   PR whose head branch is the current branch. If no PR exists, return a structured
   `blocked` result describing that the calling agent must create the PR first; the first
   implementation does not invent a PR body or push uncommitted work.
4. **Fetch review/check state.** Use direct forge APIs where available, reusing existing
   `fetch_pr_review` parsing and forge adapters. Preserve reviewer identity, verdict,
   finding/suggestion IDs, inline comments, and check conclusions in the run record.
5. **Triage review items.** Recognize `pr-auto-reviewer` verdicts and commands. Findings or
   in-scope suggestions become `changes_required` items for the calling agent, including
   their IDs, paths, rationale, and required validation. Valuable out-of-scope suggestions
   are grouped into one `create issue <id1> , <id2>` action. Incorrect, harmful, duplicate,
   or irrelevant suggestions are grouped into one `dismiss <id1> , <id2>` action with a
   required technical rationale. The command posts only actions that have not already been
   recorded as completed.
6. **Wait for approval and checks.** A review must explicitly be `Approve`; an absent,
   stale, requested-changes, or ambiguous verdict cannot pass. Required CI/CD checks must
   all be successful. Failed checks produce `blocked`; pending checks produce
   `waiting_for_ci`. No-check responses are not treated as green unless the forge explicitly
   reports that no checks are configured and repository policy allows that state.
7. **Merge through the forge.** Once approval and green checks are confirmed, invoke the
   selected forge CLI/API equivalent to:

   ```bash
   $FORGE_CLI pr merge <number> --delete
   ```

   No merge strategy flag is passed. The repository/forge default merge method therefore
   determines whether the result is a merge commit, rebase, or another configured method.
   Record the merge response and verify the PR is merged before returning `merged`.
8. **Track post-merge workflows.** Poll workflows for the merge commit until terminal. A
   failed workflow may be rerun once through the selected forge adapter, then must be
   reported as persistently failed. The result records the final workflow outcome.

## Review action API

Forge adapters will expose a small common interface for the orchestrator:

- fetch PR metadata, reviews, inline comments, commits, and checks;
- create one PR comment containing grouped `create issue` commands;
- create one PR comment containing grouped `dismiss` commands and rationale;
- merge a PR with branch deletion while leaving merge strategy unspecified;
- inspect post-merge workflow/check state and rerun one failed workflow.

GitHub and Forgejo implementations may use different transport mechanisms, but the
orchestrator must not branch on provider-specific response shapes outside the adapter.
Existing low-level helpers remain reusable; missing operations are added behind the common
adapter boundary rather than embedded in the command entry point.

## Persistence and idempotency

Run state is stored under `.agent-work/` and must be ignored or explicitly excluded from
commits. The record is keyed by forge, repository, PR number, and head SHA. It stores the
last observed review/check snapshot, posted action IDs, merge attempt, and timestamps.
Before posting a comment or rerunning a workflow, compare the action key with the record.
A changed head SHA starts a new loop revision while retaining prior history for diagnosis.
Corrupt or incompatible state is reported as `blocked` with a safe recovery suggestion;
it is never treated as approval.

## Error handling and safety

- Missing forge CLI, missing credentials, malformed PR references, unsupported forge, API
  failures, detached HEAD, dirty tree, rebase conflicts, and ambiguous reviews are explicit
  `blocked` results.
- Mutating operations require a clean, synchronized, correctly checked-out worktree.
- The command never uses `git add -A`, never pushes the default branch, and never performs
  a local merge into the default branch.
- API and CLI failures include redacted command context and actionable recovery, but never
  print tokens or credential values.
- A merge is attempted exactly once per approved head SHA. Repeated calls verify the remote
  result instead of issuing duplicate merge requests.

## Testing strategy

- Unit-test PR reference parsing, default-branch resolution, state transitions, verdict
  classification, check aggregation, action grouping, idempotency keys, exit statuses, and
  JSON serialization.
- Use fakes for git, forge APIs, and the selected forge CLI. Test GitHub and Forgejo
  response normalization independently.
- Add integration tests for a complete approved-and-green merge path, a requested-changes
  path, in-scope versus out-of-scope triage, failed/pending checks, rebase conflicts, and
  post-merge workflow retry behavior.
- Exercise the actual console entry point with `--json` in a throwaway repository fixture.
- Retain existing skill and installer tests; add a contract test that the documentation’s
  merge command matches the executable default-strategy behavior.

## Incremental delivery

1. Replace the placeholder command with context/PR resolution, structured states, and safe
   synchronization checks.
2. Add normalized review/check fetching and the agent handoff contract.
3. Add idempotent `create issue`/`dismiss` comment actions.
4. Add approved-and-green default-strategy merge with `--delete`.
5. Add post-merge workflow tracking and bounded retry behavior.
6. Update the repository-maintenance skill and user documentation to match the executable
   contract.
