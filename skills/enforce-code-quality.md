---
name: enforce-code-quality
description: Enforce complexity, architecture, source shape, and Markdown quality.
---

# Enforce Code Quality

Use the shared quality dispatcher on every edited source or Markdown file.

## Quality Standards

- Lizard enforces complexity at most 5, function length at most 50 lines, and
  at most 5 arguments.
- Semgrep enforces nesting depth at most 2, private fields, no setters, no
  inline modules, no suppression directives, and inward-only dependencies.
- Application services do not depend on inbound ports or concrete
  implementations.
- Handlers may depend on inbound ports and dispatch commands or events.
- Constructors accept at most 5 dependencies.
- Classes expose at most 5 public methods.
- Python implementation files define one primary class.
- Rust implementation files define one primary struct or trait.
- Rust implementation functions belong to that primary type.
- Rust `pub(super)` visibility is forbidden.
- Production methods do not mutate instance state outside construction hooks.
- Markdown lines are at most 100 characters.
- Markdown files are at most 300 lines.
- Markdown sections are at most 60 lines.
- Agent-generated plans, specifications, and session state are not versioned.

## Running Quality Checks

Use the installed dispatcher:

```bash
check-code-quality path/to/file.py
check-code-quality path/to/file.rs
check-code-quality path/to/guide.md
python3 scripts/check_agent_artifacts.py --staged
```

For a full repository scan:

```bash
check-code-quality
```

The dispatcher checks agent artifacts first. It then selects the Markdown
checker for `.md` and `.markdown` files. Source files receive structural,
Lizard, and Semgrep checks.

## Refactoring Guidance

Keep implementations small and delegate cross-service coordination through
commands and events. Use handlers as inbound application-port adapters.
Application services depend on outbound contracts and domain behavior.

Extract a focused class or function when a source file exceeds its shape
limits. Keep one primary Python class or Rust type per implementation file.
Move unrelated abstractions to separate files.

Replace generic setters with domain actions that validate invariants. Keep
construction-time assignments in constructors or dataclass post-initialization
hooks. Do not mutate instance state during regular behavior methods.

Split Markdown into linked files before it reaches the file or section limits.
Use one H1, a scope sentence immediately after the title, and contiguous
heading levels.

## Verification Before Claiming Done

Run the targeted tests and then the repository suite:

```bash
uv run pytest tests/ --tb=short
uv run pyright
check-code-quality
```

Confirm that all checks report success before committing or opening a pull
request.
