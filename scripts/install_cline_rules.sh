#!/usr/bin/env bash

log_info() {
  echo "[INFO] $1"
}

log_warn() {
  echo "[WARN] $1"
}

log_error() {
  echo "[ERROR] $1" >&2
}

check_agent_rules_exists() {
  local agent_rules_dir="$1"

  if [[ ! -d "$agent_rules_dir" ]]; then
    log_error "Agent rules directory not found: $agent_rules_dir"
    return 1
  fi
  log_info "Found agent_rules directory: $agent_rules_dir"
}

create_cline_dir() {
  local cline_rules_dir="$1"

  if [[ ! -d "$cline_rules_dir" ]]; then
    log_info "Creating Cline rules directory: $cline_rules_dir"
    mkdir -p "$cline_rules_dir"
  else
    log_info "Cline rules directory exists: $cline_rules_dir"
  fi
}

move_files() {
  local agent_rules_dir="$1"
  local cline_rules_dir="$2"
  shift 2
  local file
  local src
  local dest
  local failed=0

  for file in "$@"; do
    src="${agent_rules_dir}/${file}"
    dest="${cline_rules_dir}/${file}"

    if [[ ! -f "$src" ]]; then
      log_warn "File not found: $src"
      failed=$((failed + 1))
      continue
    fi

    if [[ -f "$dest" ]]; then
      log_warn "Destination already exists, backing up: $dest"
      mv "$dest" "${dest}.bak.$(date +%s)"
    fi

    mv "$src" "$dest"
    log_info "Moved: $src to $dest"
  done

  return "$failed"
}

verify_installation() {
  local cline_rules_dir="$1"
  shift
  local file
  local dest
  local all_exist=true

  log_info "Verifying installation..."
  for file in "$@"; do
    dest="${cline_rules_dir}/${file}"
    if [[ -f "$dest" ]]; then
      echo "  OK $file"
    else
      echo "  MISSING $file"
      all_exist=false
    fi
  done

  if [[ "$all_exist" == true ]]; then
    log_info "All files installed successfully!"
    return 0
  else
    log_error "Some files are missing"
    return 1
  fi
}

show_summary() {
  local agent_rules_dir="$1"
  local cline_rules_dir="$2"
  shift 2
  local file
  local index=1

  echo ""
  echo "--------------------------------------"
  echo "Cline Rules Installation Summary"
  echo "--------------------------------------"
  echo "Source: $agent_rules_dir"
  echo "Destination: $cline_rules_dir"
  echo "Files: $#"
  echo ""
  echo "Cline will load rules in order:"
  for file in "$@"; do
    echo "  $index. $file"
    index=$((index + 1))
  done
  echo ""
  echo "For more info, run:"
  echo "  cat $cline_rules_dir/00-global-noise-exclusions.md"
  echo "--------------------------------------"
}

main() {
  set -euo pipefail

  local script_dir
  local repo_root
  local agent_rules_dir
  local cline_rules_dir
  local move_status=0
  local -a files=(
    "00-global-noise-exclusions.md"
    "01-general-project-policies.md"
    "02-architecture-guidance.md"
  )

  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  repo_root="$(dirname "$script_dir")"
  agent_rules_dir="${repo_root}/agent_rules"
  cline_rules_dir="${HOME}/.cline/rules"

  echo ""
  log_info "Starting Cline rules installation..."
  echo ""

  check_agent_rules_exists "$agent_rules_dir"
  create_cline_dir "$cline_rules_dir"
  move_files "$agent_rules_dir" "$cline_rules_dir" "${files[@]}" || move_status=$?
  verify_installation "$cline_rules_dir" "${files[@]}"
  show_summary "$agent_rules_dir" "$cline_rules_dir" "${files[@]}"

  return "$move_status"
}

main "$@"
