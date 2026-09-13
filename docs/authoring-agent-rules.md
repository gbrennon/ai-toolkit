# Authoring Agent Rules

The Markdown files in `agent_rules/` are the source of the `AGENTS.md` file that
every agentic tool on this machine reads. `install-agent-rules` concatenates them
in filename order and overwrites each destination listed in the target manifest.
This guide covers adding a new rule file, improving an existing one, and
verifying the result before installing.

## How composition works

1. `install-agent-rules` reads the source directory (`agent_rules/` by default).
2. Only files matching the glob `[0-9][0-9]-*.md` are collected; everything else
   in the directory is ignored.
3. The collected files are sorted by filename and concatenated, each file's
   content stripped of trailing newlines and separated by one blank line.
4. Two header lines are prepended: a fixed marker and the source directory label.
5. Every path resolved from the manifest (plus any `--target`) is written with
   the composed content.

The composed file starts exactly like this:

```text
# Agent Rules — Composed by ai-toolkit
# Source: agent_rules

# General Purpose Noise Exclusions
...
```

Each target is written with a full overwrite — never a merge. Hand edits to
`~/.omp/agent/AGENTS.md`, `~/.agents/AGENTS.md`, or any other target are lost on
the next install. Edit the files in `agent_rules/` instead.

## File naming contract

| Requirement | Rule | Consequence if violated |
|-------------|------|-------------------------|
| Numeric prefix | Exactly two leading digits (`00`–`99`) | File is silently skipped |
| Separator | A single `-` after the two digits | File is silently skipped |
| Extension | `.md` | File is silently skipped |
| Ordering | Determined by filename sort only | Content lands in the wrong place |
| Topic name | Kebab-case, after the prefix | None — the name is informational |

Non-conforming files produce no warning and no error; the run reports a smaller
rule count and succeeds.

```text
07-git-guidance.md    conforming   — order 7, name "git-guidance"
rules.md              skipped      — no two-digit prefix
7-git.md              skipped      — single-digit prefix
```

## The current rule set

- `00-global-noise-exclusions.md` — `# General Purpose Noise Exclusions` — paths
  and file patterns agents must never read
- `01-general-project-policies.md` — `# General Project Policies` — context
  budgeting, reading strategy, secrets, testing philosophy
- `02-architecture-guidance.md` — `# Architecture Guidance` — layering, ports
  and adapters, SOLID, structural red flags
- `03-agent-communication-and-workflow.md` — `# Communication & Workflow` —
  language, tone, code-reading order, verification workflow
- `04-code-writing-style.md` — `# Code Writing Style` — naming, comments,
  docstring contract
- `05-test-writing-style.md` — `# Test Writing Style` — what to test, fakes
  versus mocks, test-first rules
- `06-markdown-writing-style.md` — `# Markdown Writing Style` — markdown
  structure, style, and composition limits
- `07-git-guidance.md` — `# Git Guidance` — git usage limits and hook policy

Put new guidance in the file that already owns the topic. Create a new file only
for a genuinely new topic.

## Adding a new rule file

1. Pick the next unused prefix. `00`–`07` are taken, so a new topic takes `08`.
2. Name the file `08-<kebab-case-topic>.md`.
3. Give it a single `#` H1 title naming the topic, then `##` (and `###`)
   subsections.
4. Write imperative bullets — one testable directive each.
5. Verify with the dry run in [Verifying a change](#verifying-a-change).
6. Install with `make install-agent-rules`.

```markdown
# Dependency Management

Rules for adding, upgrading, and removing dependencies.

## Adding a dependency

- Always add dependencies through the project's package manager, never by
  editing the lockfile by hand
- Never introduce a dependency that duplicates a capability already present

## Red flags

- A direct dependency used in exactly one function — inline it or justify it
```

Renumbering existing files is safe: order comes from filenames only, and nothing
downstream references a rule's name. Renumber only when new content must precede
existing content.

## Improving an existing rule

- Edit the file that already owns the topic, in place.
- Keep every bullet a single testable directive. If a bullet needs "and", split
  it.
- State the prohibition and the replacement behavior together. Follow the
  established phrasing: the `### One Contract Per File` bullets in
  `agent_rules/02-architecture-guidance.md` pair each "Never ..." with the
  action to take, and its `## Structural Red Flags` list pairs each symptom with
  a fix.
- Strengthen an existing bullet rather than appending a near-duplicate.
  Duplicated guidance across files is silently concatenated into the same
  `AGENTS.md`, so the agent receives the same instruction twice with no
  reconciliation.
- Delete guidance that no longer applies. Leaving it in place contradicts the
  newer rule elsewhere in the composed file.

## Drafting in `instructions/`

`instructions/*.md` (`architecture.md`, `design.md`, `quality.md`,
`restricions.md`, `solid.md`, `testing.md`) is a scratch area. No installer reads
it, and its files use `##` top-level headings rather than a single `#` title.
Treat them as drafts.

To promote a draft:

1. Merge its bullets into the `agent_rules/NN-*.md` file that owns the topic, or
   create a new numbered file with a single `#` H1 title.
2. Verify with the dry run below.
3. Run `make install-agent-rules`.

## Install targets

Destinations come from a manifest file, one path per line:

- Blank lines are ignored.
- Lines starting with `#` are comments.
- A leading `~` is expanded to the current user's home directory.

The default manifest is `~/.config/ai-toolkit/agent_targets.txt`. When it is
missing, the run seeds it with the four default targets and continues:

```text
~/.agents/AGENTS.md
~/.config/opencode/AGENTS.md
~/.omp/agent/AGENTS.md
~/.config/antigravity/AGENTS.md
```

The repo template is `agent_targets.example.txt`:

```bash
cp agent_targets.example.txt ~/.config/ai-toolkit/agent_targets.txt
```

A manifest passed explicitly with `--targets-file` is never seeded — if it does
not exist, no paths are resolved from it. Use `--target` to add a single
destination on top of the manifest targets. Duplicate paths are de-duplicated,
preserving order. Parent directories are created as needed.

## CLI reference

| Flag | Default | Description |
|------|---------|-------------|
| `--source` | `agent_rules` | Directory to read `[0-9][0-9]-*.md` rules from |
| `--targets-file` | `~/.config/ai-toolkit/agent_targets.txt` | Manifest of destination paths |
| `--target` | none | Extra single destination, appended to the manifest targets |
| `--persist` | off | Copy to `~/.config/ai-toolkit/rules.d`, then compose from there |

`--persist` writes each matching rule file into
`~/.config/ai-toolkit/rules.d` and then uses that global directory as the
composition source, so the installed `AGENTS.md` reflects the persisted copy
rather than the working tree.

Exit codes:

| Code | Meaning |
|------|---------|
| `0` | Rules composed into every resolved target |
| `1` | No matching rules found in the source directory |
| `1` | No target paths resolved from the manifest |

## Verifying a change

Run these from the repo root before installing. They compose into a scratch path
and never touch the real manifest or any real `AGENTS.md`, because the
`--targets-file` does not exist and is therefore not seeded.

```bash
uv run install-agent-rules \
  --source agent_rules \
  --targets-file /tmp/no-such-manifest.txt \
  --target /tmp/agents-preview/AGENTS.md
```

Expect `Composed 8 rules into /tmp/agents-preview/AGENTS.md` and exit status `0`.
The count must equal the number of conforming files in `agent_rules/` — a lower
count means one of your files violates the naming contract.

Then confirm the header and the rule order:

```bash
sed -n '1,4p' /tmp/agents-preview/AGENTS.md
grep -n '^# ' /tmp/agents-preview/AGENTS.md
```

Line 1 must be `# Agent Rules — Composed by ai-toolkit` and line 2
`# Source: agent_rules`, followed by the H1 titles in `00`→`07` order.

Once the preview is correct:

```bash
make install-agent-rules
```
