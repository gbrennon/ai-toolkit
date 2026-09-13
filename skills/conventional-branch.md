---
name: conventional-branch
description: >-
  Use when creating or naming git branches — defines the conventional branch
  prefix taxonomy (feat, fix, docs, release, chore) with rules for choosing the
  correct prefix and composing the slug
---

# Conventional Branch

## Overview

Name every branch consistently using a standard set of prefixes so the intent
is obvious from the name alone.

**Core principle:** One prefix per branch, slug body in kebab-case, soft limit
of 50 characters. The prefix signals *what kind of work* the branch carries;
the slug tells you *what specifically*.

**Announce at start:** "I'm using the conventional-branch skill to name this
branch."

## Process

### 1. Check for existing branches

Before proposing a branch name, check if related branches already exist:

```bash
git branch -a | grep -i <keyword>
```

If a branch already exists for the same work, reuse it. Don't create a parallel
branch.

### 2. Pick the prefix

Choose the single prefix that best describes the primary purpose of the branch.
If the work could fit two prefixes, pick the one that dominates.

### 3. Compose the slug

Turn the task description into a short, imperative kebab-case slug. Strip
filler words, skip the verb if the prefix already implies it, and keep it under
50 characters total (`<prefix>/<slug>`).

### 4. Name the branch

```bash
git checkout -b <prefix>/<slug>
```

## Prefixes

| Prefix | When | Example |
|--------|------|---------|
| `feat` | New capability, endpoint, feature, or user-facing change | `feat/oauth-token-refresh` |
| `fix` | Bug fix, patch, hotfix, or correction of incorrect behavior | `fix/null-user-in-profile` |
| `docs` | Documentation changes — new or rewritten docs or fixes | `docs/api-contract-update` |
| `release` | Release preparation — version bumps, changelog, final QA | `release/v2.1.0` |
| `chore` | Maintenance, config, dependency, refactor, or cleanup work | `chore/upgrade-pyyaml` |

## Slug Rules

1. **kebab-case** — lowercase letters, digits, and hyphens only. No
   underscores, no camelCase.
2. **Imperative mood** — write the slug as if completing a command. Prefer
   `add-login-rate-limit` over `login-rate-limit-added`.
3. **No prefix duplication** — the prefix is already in the branch path. Don't
   repeat it in the slug. `feat/add-feat-auth` is wrong;
   `feat/add-auth` is correct.
4. **No trailing slashes** — `feat/auth/` is invalid.
5. **Short and specific** — `fix/bug` is too vague;
   `fix/profile-null-on-logout` is specific.
6. **Separate words with hyphens** — `feat/oauth-token-refresh` not
   `feat/oauth_token_refresh`.

## Examples

### Good

| Branch | Reason |
|--------|--------|
| `feat/user-export-csv` | New CSV export feature |
| `fix/race-condition-cache-invalidation` | Bug fix for a specific race condition |
| `release/v3.0.0` | Preparing the v3.0.0 release |
| `chore/bump-ruff-to-0.9` | Dependency upgrade |

### Bad

| Branch | Problem |
|--------|---------|
| `feat/add-new-feat-auth` | Prefix duplication (`feat` in slug body) |
| `feature/login` | Wrong prefix — `feature` is not in the taxonomoy |
| `fix/bug` | Too vague — what bug? |
| `chore_refactor` | Missing prefix separator — no slash |
| `Feat/OAuth-Fix` | Wrong case — must be lowercase kebab-case |
| `release/v3.0.0-beta.1` | Prefer `feat/` for the work; use `release/` only for final prep |

## Boundaries

This skill **only** covers naming the branch. It does not cover:

- **Merging, pushing, or creating PRs** — delegate to
  `finishing-a-development-branch`
- **Commit message format** — delegate to `conventional-commit`; the project
  convention is one conventional commit per file
- **Git workflow strategy** (rebase vs merge, squashing) — follow project
  conventions or ask
- **Branch protection rules** — those are repository configuration, not naming

If the user asks what to *do* with the branch after creating it, hand off to
`finishing-a-development-branch`.