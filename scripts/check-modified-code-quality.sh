#!/usr/bin/env bash

extract_path() {
  printf '%s' "$1" | python3 -c \
    'import json,sys; d=json.load(sys.stdin); p=d.get("tool_input",{}).get("path",""); print(p if isinstance(p,str) else "")' \
    2>/dev/null || true
}

extract_tool() {
  printf '%s' "$1" | python3 -c \
    'import json,sys; d=json.load(sys.stdin); n=d.get("tool_name",""); print(n if isinstance(n,str) else "")' \
    2>/dev/null || true
}

extract_session() {
  printf '%s' "$1" | python3 -c \
    'import json,sys; d=json.load(sys.stdin); s=d.get("session_id",d.get("sessionId",d.get("session",""))); print(s if isinstance(s,str) else "")' \
    2>/dev/null || true
}

is_read_tool() {
  [[ "$1" == "Read" || "$1" == "read" ]]
}

is_edit_tool() {
  [[ "$1" == "Write" || "$1" == "write" ||
    "$1" == "Edit" || "$1" == "edit" ]]
}

run_breaker() {
  "$1" "$2" --session "$3" --cwd "$PWD" --path "$4"
}

emit_circuit_open() {
  printf '%s' "$1" | python3 -c \
    'import json,sys; p=json.loads(sys.stdin.read()); print(json.dumps({"continue":False,"stopReason":"Circuit breaker opened; reread the file or request help.","hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":json.dumps(p,sort_keys=True)}}))'
}

emit_terminal_feedback() {
  printf '%s\n%s' "$1" "$2" | python3 -c \
    'import json,sys; print(json.dumps({"continue":False,"stopReason":"Circuit breaker opened; reread the file or request help.","hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":sys.stdin.read()}}))'
}

emit_feedback() {
  printf '%s' "$1" | python3 -c \
    'import json,sys; print(json.dumps({"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":sys.stdin.read()}}))'
}

reset_read_tool() {
  if ! is_read_tool "$1"; then
    return 1
  fi
  run_breaker "$2" reset "$3" "$4" >/dev/null 2>&1 || true
}

handle_quality_failure() {
  local output="$1"
  local breaker="$2"
  local session_id="$3"
  local path_to_check="$4"
  local breaker_output
  local status

  set +e
  breaker_output="$(run_breaker "$breaker" failure "$session_id" "$path_to_check" 2>&1)"
  status=$?
  set -e
  if [[ $status -eq 2 ]]; then
    emit_terminal_feedback "$output" "$breaker_output"
  else
    emit_feedback "$output"
  fi
}

run_breaker_before() {
  run_breaker "$1" before "$2" "$3" 2>&1
}

run_quality_command() {
  check-code-quality "$1" 2>&1
}

handle_quality_result() {
  local status="$1"
  local output="$2"
  local breaker="$3"
  local session_id="$4"
  local path_to_check="$5"

  if [[ $status -eq 0 ]]; then
    run_breaker "$breaker" success "$session_id" "$path_to_check" >/dev/null 2>&1 || true
    return 0
  fi
  handle_quality_failure "$output" "$breaker" "$session_id" "$path_to_check"
}

run_edit_quality() {
  local breaker="$1"
  local session_id="$2"
  local path_to_check="$3"
  local breaker_output
  local output
  local status

  set +e
  breaker_output="$(run_breaker_before "$breaker" "$session_id" "$path_to_check")"
  status=$?
  set -e
  if [[ $status -eq 2 ]]; then
    emit_circuit_open "$breaker_output"
    return 0
  fi
  set +e
  output="$(run_quality_command "$path_to_check")"
  status=$?
  set -e
  handle_quality_result "$status" "$output" "$breaker" "$session_id" "$path_to_check"
}

main() {
  set -euo pipefail
  local event path_to_check tool_name session_id breaker

  event="$(cat)"
  path_to_check="$(extract_path "$event")"
  [[ -z "$path_to_check" ]] && exit 0
  tool_name="$(extract_tool "$event")"
  session_id="$(extract_session "$event")"
  session_id="${session_id:-${AI_TOOLKIT_CIRCUIT_BREAKER_SESSION:-$PWD}}"
  breaker="${AI_TOOLKIT_CIRCUIT_BREAKER_COMMAND:-ai-toolkit-hook-circuit-breaker}"
  reset_read_tool "$tool_name" "$breaker" "$session_id" "$path_to_check" && exit 0
  is_edit_tool "$tool_name" || exit 0
  run_edit_quality "$breaker" "$session_id" "$path_to_check"
}

main "$@"
