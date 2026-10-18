---
name: start-repo-maintenance
description: Start the complete autonomous repository maintenance workflow for a user task.
---

# Start Repository Maintenance

Use this skill when the user wants a task executed through the complete repository
maintenance and pull-request lifecycle.

## Invocation Contract

- Treat the user's task as the maintenance scope.
- invoke `repo-maintenance` and execute every step in its workflow.
- If the task is missing, materially incomplete, or contradictory, ask the user
  to define or clarify it before changing files.
- Ask only questions needed to establish scope, constraints, or a required
  human decision. Do not ask for routine branch, commit, review, push, or merge
  confirmation when the repository maintenance policy authorizes those actions.
- If the user provides new tasks while the workflow is active, record them,
  classify them as in-scope or follow-up work, and continue with the updated
  scope after checking the current pull request and branch state.
- Preserve unrelated user changes and never overwrite work belonging to another
  worktree.

The `repo-maintenance` skill is authoritative for branch management, quality
checks, review triage, forge operations, merge gates, post-merge verification,
release follow-up pull requests, and cleanup.
