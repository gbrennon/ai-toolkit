# Git Guidance
This guidance distinguishes local branch operations from authorized forge-based
pull request merges.

- Never push directly to `main` or merge locally into `main`.
- Authorized autonomous maintenance MAY merge an approved pull request through
  the forge after review, CI, and synchronization gates pass.
- A forge PR merge targeting `main` is not a local merge and is allowed when the
  review, CI, and synchronization gates pass.
- Use git operations required by an authorized maintenance workflow.
- Never skip hooks.
