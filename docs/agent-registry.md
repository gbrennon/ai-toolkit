# Agent Registry Operations

The agent registry manages optional per-repository agent configuration outside
the repository and resolves the effective instruction file for a worktree.

## Install the CLI

Install the unified `ai-toolkit` CLI into the active Python environment:

```bash
make install-cli
```

Every registry command runs as a subcommand of the unified CLI, invoked as
`ai-toolkit agent-registry ...`.

## Initialize the registry

Initialize the global registry once before registering repositories:

```bash
ai-toolkit agent-registry initialize
```

Pass `--registry-root PATH` to any command to select an alternate registry root,
for example when testing in a disposable directory.

## Register a repository

Register from any directory inside a Git worktree:

```bash
ai-toolkit agent-registry register /path/to/repository
```

Registration resolves the Git worktree root and its canonical `origin` remote.
It opens the generated per-repository configuration in `$VISUAL` or `$EDITOR`
for review, and the editor must exit successfully before the configuration is
stored. Pass `--no-review` to register without opening an editor.

Registration stores a managed copy at
`~/.agent-registry/repos/<repository-id>/AGENT.md`. It never creates, imports,
or overwrites the repository's local `AGENT.md`.

## Discover a repository

Resolve a registered repository's configuration and instruction source:

```bash
ai-toolkit agent-registry discover /path/to/repository
```

The command prints the repository identifier, the managed configuration path,
and the selected instruction layer and path. It validates the registry mapping
and managed artifacts, and fails closed with exit code `1` for an unregistered
repository. Discovery returns paths only and never copies instruction content
into the registry.

## Instruction precedence

Instruction resolution selects the first existing source in this order:

1. The repository's local `AGENT.md`.
2. The managed per-repository file at
   `~/.agent-registry/repos/<repository-id>/AGENT.md`.
3. A global instruction target.

A local file shadows both the managed and global layers, and the first existing
file wins. The resolver returns the selected path and never copies its content
into registry state. The host agent loads the selected path.

## Global instruction targets

The global layer reads `~/.config/ai-toolkit/agent_targets.txt`, one target path
per line, in manifest order. Blank lines and lines beginning with `#` are
ignored, and duplicate paths are removed while preserving order.

When the manifest is absent or has no usable entries, the resolver uses these
default targets in order:

```text
~/.agents/AGENTS.md
~/.config/opencode/AGENTS.md
~/.omp/agent/AGENTS.md
~/.config/antigravity/AGENTS.md
~/.pi/agent/AGENTS.md
```

Resolution never writes or modifies the manifest. If no candidate exists,
resolution reports that no instruction source was selected.

## Check registry health

Inspect the global registry with the maintenance commands:

```bash
ai-toolkit agent-registry doctor
ai-toolkit agent-registry audit
ai-toolkit agent-registry audit REPOSITORY_ID
```

`doctor` reports malformed or stale registry state. `audit` displays recorded
configuration and hook events in append order, optionally for one repository.

## Legacy rule workflow

The registry is optional and does not replace the legacy workflow. The
`install-agent-rules` command, the `agent_rules/` source, and their
manifest-based behavior remain fully supported.

Keep secrets out of local instructions, managed `AGENT.md` files, registry
metadata, and audit output.
