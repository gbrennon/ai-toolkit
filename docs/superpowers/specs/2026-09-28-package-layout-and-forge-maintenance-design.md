# Package Layout and Forge-Aware Maintenance Design

## Scope

Remove the repository's script/package split and make Python modules members of the `ai_toolkit` package. Improve repository maintenance so forge operations use the CLI associated with the current repository remote and merged feature worktrees are cleaned up safely.

## Design

- Delete `bin/` and `src/cli/`.
- Move `src/hooks/` into `src/ai_toolkit/hooks/`.
- Make packaging use the `src` layout and expose console scripts whose targets are importable `ai_toolkit` modules.
- Update installers, watchers, tests, and documentation to use package paths rather than `src.cli` or `src/hooks` paths.
- Resolve the forge from the selected git remote's host and choose the corresponding installed CLI: GitHub uses `gh`; Forgejo, Gitea, and Codeberg use `fj`; unsupported hosts produce a clear error. The resolver must not hard-code one forge CLI for every repository.
- Keep forge API adapters for operations that need them, but make maintenance forge interaction CLI-first.
- After a successful host-side merge, remove the merged source worktree and prune worktree metadata when the current process is outside that worktree. If the process is running inside it, preserve the current cwd and report cleanup for an outside/main-repository session.
- Keep branch deletion separate from worktree deletion and perform cleanup only after review and CI merge preconditions pass.

## Validation

Add or update tests for package imports, console-script targets, forge-to-CLI resolution, unsupported or unavailable CLIs, and safe worktree cleanup behavior. Run targeted tests, the full test suite, and packaging/import checks.
