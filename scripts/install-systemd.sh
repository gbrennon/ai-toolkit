#!/usr/bin/env bash
# install-systemd.sh - Install AI Toolkit systemd user services and timers

main() {
  set -euo pipefail

  local script_dir
  local systemd_dir
  local user_systemd_dir
  local unit
  local name
  local timer
  local -a units
  local -a timers

  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  systemd_dir="${script_dir}/../systemd"
  user_systemd_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

  mkdir -p "$user_systemd_dir"

  echo "==> Installing systemd user units from $systemd_dir"

  shopt -s nullglob
  units=("$systemd_dir"/*.service "$systemd_dir"/*.timer)
  timers=("$systemd_dir"/*.timer)
  for unit in "${units[@]}"; do
    name="$(basename "$unit")"
    cp "$unit" "$user_systemd_dir/$name"
    echo "    $name"
  done

  systemctl --user daemon-reload

  echo ""
  echo "==> Enabling timers..."
  for timer in "${timers[@]}"; do
    name="$(basename "$timer")"
    systemctl --user enable --now "$name"
    echo "    $name enabled and started"
  done

  echo ""
  echo "Done. Check status with: systemctl --user status 'gb-*'"
}

main "$@"
