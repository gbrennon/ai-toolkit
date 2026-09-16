#!/usr/bin/env bash
set -euo pipefail

EVENT=$(cat)
PATH_TO_CHECK=$(printf '%s' "$EVENT" | python3 -c \
  'import json,sys; d=json.load(sys.stdin); p=d.get("tool_input",{}).get("path",""); print(p if isinstance(p,str) else "")' \
  2>/dev/null || true)

if [[ -z "$PATH_TO_CHECK" ]]; then
  exit 0
fi

set +e
OUTPUT=$(check-code-quality "$PATH_TO_CHECK" 2>&1)
STATUS=$?
set -e

if [[ $STATUS -ne 0 ]]; then
  printf '%s\n' "$OUTPUT"
fi

exit "$STATUS"
