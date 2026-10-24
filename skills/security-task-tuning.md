---
name: security-task-tuning
description: >-
  Use when security-task rollouts are too easy, too hard, underspecified, or expose
  unfair, over-specified, or incomplete test coverage.
---

# Security task tuning

Tune the smallest task component that explains the evidence. Keep candidate notes
in the five-file contract and record tuning state in the candidate `index.md`.
The goal is a fair, solvable security task, not a target score manufactured by
hints or tests.

## classify before changing

- Verify the oracle is `1.0` and the environment works.
- Inspect trajectories, patches, verifier results, and trial status.
- Separate true model failures from false fails, false passes, infrastructure
  failures, and artifact download failures.
- Use the complete Realm runs manifest when downloads are incomplete.

## choose the smallest change

- **Underspecified prompt:** add a short behavioral clue that directs investigation
  without naming the vulnerable header combination, exploit request, file, helper,
  or patch. Do not provide a reproduction that gives away the solution.
- **Over-specified tests:** accept equivalent secure behavior at the public boundary;
  remove assertions about private calls, exact errors, or one implementation shape.
- **Missing security coverage:** add a deterministic fail-to-pass case for the
  required boundary and a meaningful pass-to-pass control.
- **Regression:** fix the test or gold patch only when the expected compatibility
  contract is real and documented.
- **Too easy:** remove accidental clues or duplicated coverage; do not add obscure
  requirements that the prompt does not justify.
- **Too hard:** improve the prompt only where a reasonable agent lacks necessary
  information; do not weaken the security requirement.

## evaluation rules

After changing the prompt, tests, configuration, Dockerfile, gold patch, or
repository, rerun the affected gates, the oracle, and fresh model evaluations.
Older rollouts may not be regradable against changed `instruction.md`.

The normal GPT 6.1 Sol target is `1–5/8` under the MasterDoc, with the current
team minimum being one genuine pass. If it is `0/8`, inspect the traces and follow
the latest team rule for approved fallback models.
A genuine pass from an approved model may satisfy a newer policy; Oracle success
alone does not. Confirm ambiguous policy changes with the team before submission.

## completion check

Stop tuning when the prompt is sufficient, the tests accept valid alternatives,
the gold patch closes the vulnerability, the oracle passes, and every completed
rollout has a defensible true-pass or true-fail classification. Run QC across all
current-version model runs, add trace-review comments, and record why each change
was made. Do not tune solely to raise the mean reward.
