---
name: conventional-commit
description: >-
  Create conventional commits separated by file. Prevents large multi-change
  commits by enforcing one commit per changed file.
---

Create commits grouped by file using the Conventional Commits format. Never lump
unrelated changes into a single commit.

## Process

### 1. Review all changes

Examine staged and unstaged changes:

```bash
git diff --staged --stat
git diff --staged
git status
```

If nothing is staged, include unstaged changes in the grouping:

```bash
git diff --stat
git diff
```

### 2. One commit per file

Walk through every changed file and create exactly one commit per file:

- One changed file -> one commit
- Never combine two changed files into a single commit
- Derive each commit's type and scope from that file's concern

### 3. Verify changes pass checks

Before presenting the commit plan, verify the changes are clean:

**Type checks:**
```bash
uv run pyright
```

**Tests:**
```bash
make test
```

**Docs in sync:**
Check that any changed public API, config, CLI surface, or user-facing behavior
has corresponding doc updates. Grep for related doc files and verify they
reflect the changes. If the project has a doc-generation pipeline, run it to
confirm no warnings.

If any check fails, fix the issues before proceeding. Do not commit broken code.

If the project does not have `make test`, use the equivalent project command
(e.g., `pytest`, `npm test`). If no verification tooling exists, note it but
still proceed — never skip verification just because it requires finding the
right command.

### 4. Present commit plan for approval

Before running `git commit`, present the full plan as a numbered list:

```
1. feat(auth): add OAuth refresh token rotation
2. fix(api): handle null user in profile endpoint
3. chore(deps): upgrade lodash to 4.17.21
```

For each proposed commit include: type, scope, subject line, and a brief note
of what files it covers. Ask for approval before executing.

### 5. Commit each file

Commit each file separately using `git commit` with the Conventional Commits
format. Stage only the current file before each commit.

## Commit Format

### Subject line

`<type>(<scope>): <imperative summary>`

- `<scope>` is optional but encouraged
- Types: `feat`, `fix`, `refactor`, `perf`, `docs`, `test`, `chore`, `build`,
  `ci`, `style`, `revert`
- Imperative mood: "add", "fix", "remove" — not "added", "adds", "adding"
- Hard cap at 72 characters, aim for 50 or fewer
- No trailing period
- Match project convention for capitalization after the colon

### Body (only when needed)

Include a body when the subject alone does not answer *why* the change was
made. Required for:

- Breaking changes (also include `BREAKING CHANGE:` trailer)
- Security fixes
- Data migrations
- Reverts (reference the original commit)
- Non-obvious design decisions

Body formatting:

- Wrap at 72 characters
- Bullets use `-` not `*`
- Reference issues/PRs at the end: `Closes #42`, `Refs #17`

### What never goes in

- "This commit does X", "I", "we", "now", "currently" — the diff says what
- "As requested by..." — use `Co-authored-by:` trailer instead
- AI attribution of any kind — unless the user's own rule requires an
  `Assisted-by` trailer
- Emoji (unless the project convention requires it)
- Restating the file name when the scope already conveys it

## Examples

Diff adds an API endpoint across two files and fixes a null pointer bug in a
third:

Present plan:
```
1. feat(api): add GET /users/:id/preferences
   Files: src/routes/users.ts

2. feat(service): add preferences query
   Files: src/services/preferences.ts

3. fix(auth): guard against null session in middleware
   Files: src/middleware/auth.ts
```

Diff renames a database column and adds a migration:

```
1. feat(db): rename `orders.status` to `orders.state`

   BREAKING CHANGE: Existing queries referencing `orders.status` must
   migrate to `orders.state`. Migration v003 handles the rename.
```

## Boundaries

This skill produces a commit plan for user approval and then executes each
commit. It does not amend history (`--amend`), force-push, or operate outside
the current branch without explicit user instruction.