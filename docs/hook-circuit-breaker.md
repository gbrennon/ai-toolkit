# Hook Circuit Breaker

The quality hook stops retry loops after three consecutive failed checks for one
session, working directory, and file.

## Behavior

- A successful quality check resets the target failure count.
- The third consecutive failure opens the circuit.
- Further attempts are rejected before running the quality checker.
- Open-circuit failures emit one JSON object with `status` set to `terminal`.
- Pi receives quality feedback through PostToolUse `additionalContext` and a
  `continue: false` stop signal.
- Reading the affected file resets its circuit; the CLI also supports `reset`
  for explicit recovery.

State is stored at `$XDG_STATE_HOME/ai-toolkit/hook-circuit-breaker.json`, or at
`~/.local/state/ai-toolkit/hook-circuit-breaker.json` when that variable is not
set. Set `AI_TOOLKIT_CIRCUIT_BREAKER_STATE` for isolated tests or temporary
sessions.

The guard is deliberately separate from the quality checker. Install it with
`make install-quality-cli`; the installed command is
`ai-toolkit-hook-circuit-breaker`.

## Limitation

A PostToolUse hook cannot undo the completed tool action or force Pi or OMP to
change strategy. It can stop later hook processing and provide the agent with a
precise recovery instruction, reducing wasted retries while the runtime decides
how to present or act on that result.
