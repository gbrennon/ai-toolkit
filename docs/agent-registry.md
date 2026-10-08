# Agent Registry Operations

`agent-registry` is the command-line interface for the global agent registry. The
registry stores managed `AGENT.md` files below `~/.agent-registry`, outside the
repository. Registry operations never create or update an `AGENT.md` in the
repository.

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
then opens the generated global configuration in `$VISUAL` or `$EDITOR` for
review. The editor must exit successfully before the configuration is stored.

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

The registry is the only authority for managed agent configuration. Keep secrets
out of `AGENT.md`, registry metadata, and audit output.
