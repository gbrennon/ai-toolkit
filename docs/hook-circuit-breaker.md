# Hook Circuit Breaker

The quality hook stops retry loops after three consecutive failed checks for one
session, working directory, and file.

## Behavior

- A successful quality check resets the target failure count.
- The third consecutive failure opens the circuit.
- Further attempts are rejected before running the quality checker.
- Open-circuit failures emit one JSON object with `status` set to `terminal`.
- Terminal feedback uses passive PostToolUse `hookSpecificOutput.additionalContext`
  containing recovery guidance and the quality or circuit-breaker diagnostics.
- Terminal feedback leaves the active Pi model request alive and does not roll back
  the completed edit.
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
change strategy. Terminal feedback leaves the active model request alive while
providing a precise recovery instruction and diagnostics through passive
`hookSpecificOutput.additionalContext`.
