---
name: security-task-authoring
description: Use when authoring or packaging a security task.
---

# Security task authoring

Use the installed `riftbridge` CLI and the `rv` task schema. Treat the task
folder as a submission artifact, not as a normal application repository.

For candidate planning, keep exactly five files in each candidate directory:
`index.md`, `instructions.md`, `proposal.md`, `reasoning.md`, and `vuln-type.md`.
Use `index.md` as the navigation and lifecycle record. Keep submission ZIPs,
rollout artifacts, QC output, and temporary handoffs outside candidate directories.

## authoring rules

- The human author writes `instruction.md` and `reasoning.txt` personally. AI may
  inspect repositories, run experiments, and perform mechanical checks, but must
  not generate, rewrite, or polish those files.
- The human author reviews and explains the prompt, vulnerability, gold patch, and
  every protected test. Do not use AI to write that review feedback.
- Preserve human-authored `instructions.md` and `reasoning.md` prose; AI may update
  navigation and mechanical status records but must not invent the author's voice.
- Follow the current task master document and the task's `AGENTS.md`. If they differ,
  use the newer authoritative team guidance and record unresolved conflicts.

## submission boundaries

- `rv submit` archives almost the whole task directory. Keep generated `jobs/`,
  `.agents/`, `submission.zip`, and `node_modules` out of the deliverable; treat
  `.seaworthy/` as unsafe authoring space too.
- Keep temporary logs, build output, caches, credentials, VM state, and research
  scratch files under `/tmp`, not in the task directory.
- Do not commit task changes unless the author explicitly asks.
- Do not commit changes inside `environment/repo` as a substitute for the gold
  patch. The vendored repository must start at the vulnerable base commit.

## tests and patch

- `solution/gold_patch.diff` contains only the reference implementation.
- `tests/test_patch.diff` contains tests only. Protected tests should live in a
  separate repository test file when possible.
- `protected_paths` may contain test files or fixtures, never production paths.
- Every fail-to-pass test must fail on the vulnerable base and pass with the fix.
  Include meaningful pass-to-pass controls; do not add duplicate tests to meet a
  numeric threshold.
- Test public behavior with deterministic offline fixtures. Equivalent secure
  implementations must remain acceptable; do not assert private calls or exact
  error strings without a real contract.
- Keep `test_cmd`, parser names, and IDs synchronized with actual test output.

## schema and wrappers

`rv init` does not detect the repository language. Set `metadata.repo_language`,
the numeric `task_id`, and the single author with the author's approved
address. The host/VM git email can differ.

Run checks through `riftbridge`, never host-side Docker or host-side `rv`:

```bash
riftbridge verification
riftbridge oracle
riftbridge submit /path/to/task
```

`riftbridge submit` runs deterministic checks by default. Full LLM and probe
checks are opt-in with `FULL_CHECK=1`, for example:

```bash
FULL_CHECK=1 riftbridge submit /path/to/task
```

Before submission, inspect the task file list for `.seaworthy`, caches, logs, and
temporary files. `riftbridge submit`
starts the VM when needed; do not run `riftbridge vm start` first.

## rollout handoff

- Treat the latest team guidance as authoritative when it updates an older
  MasterDoc.
- A completed `succeeded` rollout is not automatically a pass. Verify its reward,
  verifier result, trajectory, and trial status.
- Distinguish download failures from model failures using the complete Realm runs
  manifest. `Request aborted` means the artifact download failed, not that the
  model failed.
- If GPT 6.1 Sol is `0/8`, inspect the traces and use only the approved fallback
  path allowed by current team guidance. Count a genuine pass from an approved
  model, not an Oracle or infrastructure result.
- A changed `instruction.md` can make older rollouts unavailable for regrade;
  run fresh evaluations against the new instruction.
- Do not add another model merely to manufacture a target score. Record the model
  and policy that justify every extra evaluation.
- The current team minimum is one genuine Frontier pass; retain the documented
  `1–5/8` range unless newer team guidance explicitly changes the maximum.
