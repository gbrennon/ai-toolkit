#!/usr/bin/env bash

main() {
  set -euo pipefail

  local event
  local path_to_check
  local output
  local status
  local session_id
  local breaker
  local breaker_output
  local tool_name

  event="$(cat)"
  path_to_check="$(printf '%s' "$event" | python3 -c \
    'import json,sys; d=json.load(sys.stdin); p=d.get("tool_input",{}).get("path",""); print(p if isinstance(p,str) else "")' \
    2>/dev/null || true)"
  tool_name="$(printf '%s' "$event" | python3 -c \
    'import json,sys; d=json.load(sys.stdin); n=d.get("tool_name",""); print(n if isinstance(n,str) else "")' \
    2>/dev/null || true)"

  if [[ -z "$path_to_check" ]]; then
    exit 0
  fi

  session_id="$(printf '%s' "$event" | python3 -c \
    'import json,sys; d=json.load(sys.stdin); s=d.get("session_id",d.get("sessionId",d.get("session",""))); print(s if isinstance(s,str) else "")' \
    2>/dev/null || true)"
  session_id="${session_id:-${AI_TOOLKIT_CIRCUIT_BREAKER_SESSION:-$PWD}}"
  breaker="${AI_TOOLKIT_CIRCUIT_BREAKER_COMMAND:-ai-toolkit-hook-circuit-breaker}"

  if [[ "$tool_name" == "Read" || "$tool_name" == "read" ]]; then
    "$breaker" reset --session "$session_id" --cwd "$PWD" --path "$path_to_check" >/dev/null 2>&1 || true
    exit 0
  fi

  set +e
  breaker_output="$("$breaker" before --session "$session_id" --cwd "$PWD" --path "$path_to_check" 2>&1)"
  status=$?
  set -e
  if [[ $status -eq 2 ]]; then
    printf '%s' "$breaker_output" | python3 -c \
      'import json,sys; p=json.loads(sys.stdin.read()); print(json.dumps({"continue":False,"stopReason":"Circuit breaker opened; reread the file or request help.","hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":json.dumps(p,sort_keys=True)}}))'
    exit 0
  fi

  set +e
  output="$(check-code-quality "$path_to_check" 2>&1)"
  status=$?
  set -e

  if [[ $status -ne 0 ]]; then
    set +e
    breaker_output="$("$breaker" failure --session "$session_id" --cwd "$PWD" --path "$path_to_check" 2>&1)"
    status=$?
    set -e
    if [[ $status -eq 2 ]]; then
      output="$output
$breaker_output"
      printf '%s' "$output" | python3 -c \
        'import json,sys; print(json.dumps({"continue":False,"stopReason":"Circuit breaker opened; reread the file or request help.","hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":sys.stdin.read()}}))'
      exit 0
    fi
    printf '%s' "$output" | python3 -c \
      'import json,sys; print(json.dumps({"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":sys.stdin.read()}}))'
    exit 0
  fi

  "$breaker" success --session "$session_id" --cwd "$PWD" --path "$path_to_check" >/dev/null 2>&1 || true
  exit 0
}

main "$@"
