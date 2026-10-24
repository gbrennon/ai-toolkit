---
name: security-task-validation
description: >-
  Use when validating a security task, interpreting rv results, or
  reviewing agent rollouts before submission.
---

# Security task validation

Validate the current task content, not an earlier task snapshot. Route local checks
through the installed `riftbridge` CLI; do not invoke Docker or `rv` directly on
the host. Keep candidate notes to the five standard files and use each
`index.md` as the navigation/status entrypoint.

## automated gates

Run these in order:

1. `riftbridge verification` for wrapped `rv check` checks.
2. `riftbridge oracle` and confirm the trial exits cleanly, every configured test
   is parsed, and the reference reward is `1.0`.
3. `riftbridge submit /path/to/task` to package the task after review.

The submission command runs deterministic checks by default. Use
`FULL_CHECK=1 riftbridge submit /path/to/task` explicitly for the full LLM and
probe pipeline. A full-check probe
timeout is not a model result and must not be silently counted as a model failure.

## evidence review

For each task edit, compare the current prompt, tests, gold patch, repository SHA,
and verifier configuration. Confirm that:

- the vulnerable base fails every fail-to-pass test;
- the gold patch passes every fail-to-pass and pass-to-pass test;
- tests grade public security behavior rather than one implementation shape;
- fixtures are deterministic and offline;
- protected paths contain tests or fixtures, not production code;
- the repository and advisory support a real, reachable vulnerability.

Classify failures as task ambiguity, unfair coverage, incomplete gold patch,
regression, environment failure, infrastructure failure, or genuine agent failure.
A setup error, empty trajectory, connection failure, pre-action timeout, or failed
artifact download is infrastructure evidence, not a model failure.

## rollout review

Review every completed rollout, including passes and fails. Check the reward,
verifier result, trial status, trajectory, final patch, and final answer. A
`succeeded` status alone is insufficient. Use the complete Realm runs manifest to
separate `Request aborted` downloads from actual model outcomes. Review all model
runs, including passes, and keep Oracle runs separate from model-pass counts.

After changing `instruction.md`, tests, configuration, Dockerfile, gold patch, or
repository state, treat prior evidence as stale. Run fresh evaluations; older
rollouts may not be regradable against the changed instruction.

If GPT 6.1 Sol is `0/8`, inspect the traces before changing the task. Follow the
latest team policy for approved zero-pass fallback models and count a genuine pass,
not an Oracle or infrastructure result. Do not submit as though the normal target
was met without the required pass or explicit team approval.

## manual Realm steps

The browser actions are not replaced by local automation: upload the archive,
select Validate & Build, confirm golden validation is 100%, queue the permitted
model runs, inspect trajectories, add a trace review for every rollout, and submit
for HDM review only after every completed rollout is classified as a true pass or
true fail.

Do not claim readiness until the current task content, refreshed oracle result,
rollout classifications, and submission checks all agree. The current team minimum
is one genuine Frontier pass; the documented target remains `1–5/8` unless newer
team guidance explicitly changes it. Run Realm QC on all current-version model
runs as review evidence, then add trace-review comments for every rollout; QC does
not replace the human classification or the final HDM submission.
