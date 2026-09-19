#!/usr/bin/env bash
# check-code-quality.sh - Run Lizard complexity and Semgrep structural checks

usage() {
  cat << 'EOF'
Usage: check-code-quality [OPTIONS] [DIRECTORY]

Enforces code quality standards using Lizard (quantitative complexity)
and Semgrep (structural rules and conventions).

Arguments:
  DIRECTORY                     Target directory to scan (default: current directory .)

Options:
  --init                        Initialize .semgrep/ in target directory with bundled rules
  -C, --max-complexity <int>    Maximum cyclomatic complexity (default: 5)
  -L, --max-length <int>        Maximum function length in lines (default: 50)
  -a, --max-args <int>          Maximum function arguments (default: 5)
  --semgrep-config <path>       Custom Semgrep rules config file or directory
  --only-lizard                 Run only Lizard complexity analysis
  --only-semgrep               Run only Semgrep structural analysis
  -h, --help                    Display this help message and exit

Examples:
  check-code-quality
  check-code-quality src/
  check-code-quality --init
  check-code-quality -C 4 -L 40
  check-code-quality --only-lizard
  check-code-quality --only-semgrep
EOF
}

find_source_rules() {
  local global_rules_dir="$1"
  local repo_rules_dir="$2"

  if [[ -d "$global_rules_dir" ]] && compgen -G "$global_rules_dir/*.yml" > /dev/null; then
    echo "$global_rules_dir"
  elif [[ -d "$repo_rules_dir" ]] && compgen -G "$repo_rules_dir/*.yml" > /dev/null; then
    echo "$repo_rules_dir"
  else
    echo ""
  fi
}

resolve_semgrep_config() {
  local configured="$1"
  local target="$2"
  local global_rules_dir="$3"
  local repo_rules_dir="$4"

  if [[ -n "$configured" ]]; then
    echo "$configured"
    return
  fi

  if [[ -d "$target/.semgrep" ]] && compgen -G "$target/.semgrep/*.yml" > /dev/null; then
    echo "$target/.semgrep"
    return
  fi

  if [[ -d "$global_rules_dir" ]] && compgen -G "$global_rules_dir/*.yml" > /dev/null; then
    echo "$global_rules_dir"
    return
  fi

  if [[ -d "$repo_rules_dir" ]] && compgen -G "$repo_rules_dir/*.yml" > /dev/null; then
    echo "$repo_rules_dir"
    return
  fi

  echo ""
}

check_lizard() {
  if ! command -v lizard > /dev/null 2>&1; then
    echo "Error: 'lizard' executable not found in PATH." >&2
    echo "Install it via: pipx install lizard or pip install lizard" >&2
    return 1
  fi
}

check_semgrep() {
  if ! command -v semgrep > /dev/null 2>&1; then
    echo "Error: 'semgrep' executable not found in PATH." >&2
    echo "Install it via: pipx install semgrep or pip install semgrep" >&2
    return 1
  fi
}

main() {
  set -euo pipefail

  local script_dir
  local repo_rules_dir
  local global_rules_dir
  local max_complexity=5
  local max_length=50
  local max_args=5
  local semgrep_config=""
  local only_lizard=false
  local only_semgrep=false
  local init_mode=false
  local target=""
  local source_rules
  local dest_dir
  local resolved_config
  local exit_code=0
  local lizard_status
  local semgrep_status

  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  repo_rules_dir="$(cd "$script_dir/.." && pwd)/rules/semgrep"
  global_rules_dir="${HOME}/.config/ai-toolkit/semgrep"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --init)
        init_mode=true
        shift
        ;;
      -C|--max-complexity)
        if [[ -z "${2:-}" ]]; then
          echo "Error: $1 requires an integer argument" >&2
          exit 1
        fi
        max_complexity="$2"
        shift 2
        ;;
      -L|--max-length)
        if [[ -z "${2:-}" ]]; then
          echo "Error: $1 requires an integer argument" >&2
          exit 1
        fi
        max_length="$2"
        shift 2
        ;;
      -a|--max-args)
        if [[ -z "${2:-}" ]]; then
          echo "Error: $1 requires an integer argument" >&2
          exit 1
        fi
        max_args="$2"
        shift 2
        ;;
      --semgrep-config)
        if [[ -z "${2:-}" ]]; then
          echo "Error: $1 requires a path argument" >&2
          exit 1
        fi
        semgrep_config="$2"
        shift 2
        ;;
      --only-lizard)
        only_lizard=true
        shift
        ;;
      --only-semgrep)
        only_semgrep=true
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      -*)
        echo "Unknown option: $1" >&2
        usage >&2
        exit 1
        ;;
      *)
        if [[ -z "$target" ]]; then
          target="$1"
        else
          echo "Unexpected extra argument: $1" >&2
          exit 1
        fi
        shift
        ;;
    esac
  done

  target="${target:-.}"

  if [[ "$init_mode" == true ]]; then
    source_rules="$(find_source_rules "$global_rules_dir" "$repo_rules_dir")"
    if [[ -z "$source_rules" ]]; then
      echo "Error: Could not locate source Semgrep rules (checked $global_rules_dir and $repo_rules_dir)" >&2
      exit 1
    fi

    dest_dir="$target/.semgrep"
    mkdir -p "$dest_dir"
    cp -v "$source_rules"/*.yml "$dest_dir/"
    echo "Initialized Semgrep rules in $dest_dir"
    exit 0
  fi

  if [[ "$only_semgrep" == false ]]; then
    check_lizard
    echo "=== Running Lizard Complexity Analysis ==="
    echo "Limits: Cyclomatic Complexity <= $max_complexity, Function Length <= $max_length, Arguments <= $max_args"
    echo "Target: $target"
    echo ""

    set +e
    lizard -C "$max_complexity" -L "$max_length" -a "$max_args" -i 0 "$target"
    lizard_status=$?
    set -e

    if [[ $lizard_status -ne 0 ]]; then
      echo "Lizard detected complexity violations" >&2
      exit_code=1
    else
      echo "Lizard complexity analysis passed"
    fi
    echo ""
  fi

  if [[ "$only_lizard" == false ]]; then
    check_semgrep
    resolved_config="$(resolve_semgrep_config "$semgrep_config" "$target" "$global_rules_dir" "$repo_rules_dir")"
    if [[ -z "$resolved_config" ]]; then
      echo "Error: No Semgrep configuration found. Checked:" >&2
      echo "  - $target/.semgrep" >&2
      echo "  - $global_rules_dir" >&2
      echo "  - $repo_rules_dir" >&2
      echo "Run with --init or specify --semgrep-config <path>" >&2
      exit 1
    fi

    echo "=== Running Semgrep Structural Analysis ==="
    echo "Config: $resolved_config"
    echo "Target: $target"
    echo ""

    set +e
    semgrep scan --config "$resolved_config" --error "$target"
    semgrep_status=$?
    set -e

    if [[ $semgrep_status -ne 0 ]]; then
      echo "Semgrep detected structural or architectural violations" >&2
      exit_code=1
    else
      echo "Semgrep structural analysis passed"
    fi
    echo ""
  fi

  if [[ $exit_code -ne 0 ]]; then
    echo "Code quality checks failed. Please refactor violations above before completing work." >&2
    exit 1
  fi

  echo "All code quality checks passed."
}

main "$@"
