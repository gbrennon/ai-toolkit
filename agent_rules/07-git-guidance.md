# Git Guidance

This guidance distinguishes local branch operations from authorized forge-based
pull request operations.

## Local branch protection

- Never push directly to `main`.
- Never merge locally into `main`.
- Use a feature branch for all committed work.

## Authorized forge operations

- Agents MAY push feature branches and open or update pull requests.
- Agents MAY inspect pull request reviews, comments, statuses, and workflow runs.
- Agents MAY post documented review-triage comments on pull requests.
- Agents MAY merge an approved pull request through the forge after review, CI,
  and synchronization gates pass.
- A forge pull request merge targeting `main` is not a local merge.
- Use the repository's default forge merge strategy and branch-deletion option.
- Use git operations required by an authorized maintenance workflow.
- Never skip git hooks.
