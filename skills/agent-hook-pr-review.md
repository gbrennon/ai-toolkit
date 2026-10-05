---
name: agent-hook-pr-review
summary: Polls pull-request reviews and reports a review for the current head
---

# Agent Hook: PR Review Listener

This skill documents the installed `agent-hook-pr-review` command. The command
polls a forge review endpoint and reports the latest review that matches the
pull-request head captured when polling begins.

## Usage

Run the hook after opening a pull request or pushing a new head:

```bash
agent-hook-pr-review <PR-URL | owner/repo/number> --listen
```

Run without `--listen` to check once:

```bash
agent-hook-pr-review <PR-URL | owner/repo/number>
```

The command prints the matching review as JSON. It does not modify code, create
issues, update pull requests, or merge branches.

## Polling Contract

- The command reads the current pull-request head before polling begins.
- Reviews for older commits do not satisfy the wait.
- `--listen` continues until a current-head review appears.
- Polling uses capped incremental backoff: `30s`, `60s`, `120s`, `240s`, then
  `300s`.
- The command exits after one check when `--listen` is omitted.

## Maintenance Integration

`repo-maintenance` starts this hook after opening or updating a pull request.
When the command reports a review, use `pr-interaction` to retrieve the
complete review, inspect its freshness, and perform review triage.

The hook does not implement webhook events, CI monitoring, caching,
`.agenthookrc` configuration, or automated maintenance actions.