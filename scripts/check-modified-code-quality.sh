#!/usr/bin/env bash

main() {
  set -euo pipefail

  local event
  local path_to_check
  local output
  local status

  event="$(cat)"
  path_to_check="$(printf '%s' "$event" | python3 -c \
    'import json,sys; d=json.load(sys.stdin); p=d.get("tool_input",{}).get("path",""); print(p if isinstance(p,str) else "")' \
    2>/dev/null || true)"

  if [[ -z "$path_to_check" ]]; then
    exit 0
  fi

  set +e
  output="$(check-code-quality "$path_to_check" 2>&1)"
  status=$?
  set -e

  if [[ $status -ne 0 ]]; then
    printf '%s\n' "$output"
  fi

  exit "$status"
}

main "$@"
