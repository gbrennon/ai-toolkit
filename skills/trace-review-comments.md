---
name: trace-review-comments
description: >-
  Use when writing review comments for agent traces, task submissions, verifier
  artifacts, or run UUIDs that need evidence-based pass or fail explanations.
---

# trace review comments

write short plain-text comments about code and trace evidence. the comments are
for the person reviewing the task, not for the author to review themself.

## style

- use informal lowercase writing similar to the user's chat messages.
- typos and loose grammar are allowed, but evidence values stay exact.
- keep comments small, usually two or three sentences per trace.
- do not use markdown tags, `@` mentions, reviewer labels, or code fences.
- do not mention private confusion, exploratory directories, guessed IDs, or
  unavailable artifacts.

## source of truth

1. locate the extracted artifacts and zip artifacts requested by the user.
2. list exact run IDs from filenames, manifests, supplied HTML, or task records.
3. use artifacts and supplied platform HTML as the source of truth.
4. keep only IDs present in the platform record and an available artifact.
5. never invent, shorten, or silently correct a run ID.

## evidence round

For every included trace, read verifier results and record:

- complete run UUID and model, when scope matters
- `fail_to_pass_total` and `fail_to_pass_passed`
- `pass_to_pass_total` and `pass_to_pass_passed`
- `graded_tests_modified_by_agent` and `harness_error`
- `reward` and `resolved`
- exact failed test names
- changed production and test files in the patch

Use exact verifier terms: `fail-to-pass`, `pass-to-pass`, `reward`, `resolved`,
and `harness error`. Prefer these over vague wording such as “regression tests”.

## comment round

A genuine pass comment explains that all fail-to-pass and pass-to-pass tests
passed, no graded tests changed, and no harness error occurred. Mention the
production patch when it proves the result is not test-only.

A genuine fail comment gives the exact ratio, names failed tests or their common
behavior, and distinguishes a code failure from a harness failure. Mention
unchanged pass-to-pass tests and test-integrity evidence when available.

If a verifier pass is outside the requested model or platform scope, call it
out of scope rather than calling it a counted pass or a verifier failure.

## verification rounds

### evidence review

Check every sentence against the artifacts:

- every UUID matches both a supplied platform ID and an artifact filename
- every count, status, reward, and integrity claim matches verifier JSON
- every named test or technical phrase exists in results, the patch, or trace
- every claimed code behavior appears in the patch or trace output

Remove unsupported claims. If evidence conflicts, state the conflict plainly.

### wording review

Read the final file as comments ready to paste into a platform review. Confirm
that comments address the trace and code, not the task author personally; use
informal lowercase wording; preserve exact technical values; and expose no
private paths, confusion, guessed IDs, or unrelated artifacts.

### final ID and phrase review

Extract every UUID from the output and compare it with the supplied platform IDs.
Search quoted test names and technical phrases in the artifacts. Search for
placeholders such as `some-uuid`, shortened IDs, `TODO`, and unsupported
“regression test” wording. Reread the output after edits.

Only report completion when the output contains verified comments for the
intended traces and no unverified IDs or claims.
