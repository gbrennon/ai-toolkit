---
name: pr-interaction
description: Use when interacting with pull requests through a git forge
---

# Pull Request Interaction

This skill owns forge-specific pull-request operations. `repo-maintenance` owns
branch, quality, review-loop, and merge policy; this skill owns the commands and
API resources used to inspect and update a pull request.

## Select the forge

Select one forge CLI from the repository remote before the first forge operation:

```bash
if command -v forge-detect >/dev/null 2>&1; then
  FORGE_CLI="$(forge-detect --cli)"
else
  REMOTE_NAME="${REMOTE:-$(
    git config --get "branch.$(git branch --show-current).remote" 2>/dev/null ||
      git remote | { IFS= read -r first; printf '%s' "$first"; }
  )}"
  REMOTE_URL="$(git remote get-url "$REMOTE_NAME")"
  case "$REMOTE_URL" in
    *github.com*) FORGE_CLI=gh ;;
    *codeberg.org*|*forgejo*|*gitea*) FORGE_CLI=fj ;;
    *)
      printf 'Cannot select a forge CLI for remote: %s\n' "$REMOTE_URL" >&2
      exit 1
      ;;
  esac
fi

command -v "$FORGE_CLI" >/dev/null 2>&1 || {
  printf '%s is required for this repository remote\n' "$FORGE_CLI" >&2
  exit 1
}
```

Inspect the selected CLI before using it:

```bash
"$FORGE_CLI" --help
"$FORGE_CLI" pr --help
```

Use only commands and flags documented by that installed CLI. Use its API
adapter when the CLI cannot represent a response or operation correctly.

## Pull-request state

For an existing pull request, retrieve these resources as needed:

- Pull-request metadata, including state, base, head, and mergeability.
- Pull-request commits to identify the current head commit.
- Pull-request changed files to establish review scope.
- Pull-request reviews, including verdict, review commit, findings, and
  suggestions.
- Pull-request comments to verify triage commands and issue links.
- Commit statuses and workflow runs to verify CI explicitly.

A review is fresh only when its review commit matches the current pull-request
head. An empty, malformed, or unsupported status response is not green. Report
CI as unavailable and keep the merge blocked until the repository policy is
satisfied.

## Waiting for reviews

Use the installed review hook after opening or updating a pull request:

```bash
agent-hook-pr-review <PR-URL | owner/repo/number> --listen
```

The hook captures the current head before polling and uses capped incremental
backoff. Use `agent-hook-pr-review` for waiting; use the forge review resource
for complete review content and freshness verification.

## Review retrieval and triage

Read the complete review before acting. Classify each finding and suggestion by
correctness, scope, and risk.

For a valuable deferred suggestion, post one batched command in a pull-request comment:

```text
create issue <ids>
```

For an invalid, harmful, duplicate, or irrelevant suggestion, post one batched
command in a pull-request comment:

```text
dismiss <ids>
```

Here, `<ids>` is the comma-separated review suggestion list, for example
`<id1> , <id2> , <id3>`. Use exactly one of these command forms for every
suggestion. Never invoke an issue creation command manually and never create or
dismiss suggestions outside the pull-request comment command.

Verify the command outcome in the pull-request comments and issue list. If the
command is not processed within the documented wait, keep the command comment
as the recorded triage decision and report the unprocessed state. Do not use a
direct issue-creation fallback and do not create duplicate issues.

## Pull-request lifecycle operations

Use the selected forge to perform these operations:

- Search for an existing pull request before creating one.
- Create a pull request with motivation, scope, changes, validation, follow-ups,
  and review notes.
- Update the pull-request body when scope changes.
- Post comments for review commands, triage rationale, and blockers.
- Inspect the installed merge command before merging.
- Use the repository default merge strategy and documented branch-deletion flag.

`repo-maintenance` decides whether merge preconditions are satisfied. This skill
must not treat forge-level mergeability as permission to merge.

## Boundaries

This skill does not own local implementation, branch synchronization, test
execution, review policy, or merge authorization. It provides the forge
interaction needed by those workflows.
