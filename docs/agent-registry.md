# Agent Registry Operations

`agent-registry` manages optional per-repository agent configuration outside the
repository. Registry operations never create or update an `AGENT.md` in the
repository.

## Instruction precedence

Instruction resolution uses the first existing source in this order:

1. The repository's local `AGENT.md`.
2. The managed per-repository file at
   `~/.agent-registry/repos/<repository-id>/AGENT.md`.
3. A global-global instruction target.

A local file shadows both registry layers. The resolver checks whether the local
file exists, returns its path, and does not copy its content into registry state.
The host agent is responsible for loading the selected path.

The global-global target is selected from `~/.config/ai-toolkit/agent_targets.txt`
in manifest order. Blank lines and comments are ignored, and the first existing
target wins. When the manifest does not exist, the resolver checks these default
targets in order:

```text
~/.agents/AGENTS.md
~/.config/opencode/AGENTS.md
~/.omp/agent/AGENTS.md
~/.config/antigravity/AGENTS.md
~/.pi/agent/AGENTS.md
```

If no candidate exists, discovery reports that no instructions were selected.
The legacy rule source and installer remain available; adopting the registry is
optional.

## Initialize

Install the CLI, then initialize the global registry once:

```bash
make install-cli
agent-registry initialize
```

Use `--registry-root PATH` with any command to select an alternate registry root,
for example when testing in a disposable directory.

## Register a repository

Run registration from any directory in a Git worktree:

```bash
agent-registry register /path/to/repository
```

Registration resolves the Git worktree root and its canonical `origin` remote,
then opens the generated per-repository configuration in `$VISUAL` or `$EDITOR`
for review. The editor must exit successfully before the configuration is stored.

Registration never imports or overwrites a repository-local `AGENT.md`.

## Discover instructions

Resolve a repository's instruction source with:

```bash
agent-registry discover /path/to/repository
```

The command reports the selected source path and its layer. Discovery validates
the selected registry mapping and managed artifacts, but local instruction
content is not copied into the registry or used to mutate registry metadata.

## Check registry health

Use the maintenance commands to inspect the global registry:

```bash
agent-registry doctor
agent-registry audit
agent-registry audit REPOSITORY_ID
```

`doctor` reports malformed or stale registry state. `audit` displays recorded
configuration and hook events in append order.

## Migrate a record

Migration changes registry metadata without importing repository-local
configuration:

```bash
agent-registry migrate REPOSITORY_ID
```

Keep secrets out of local instructions, managed `AGENT.md` files, registry
metadata, and audit output.
