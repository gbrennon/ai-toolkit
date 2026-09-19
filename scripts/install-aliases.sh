#!/usr/bin/env bash
# install-aliases.sh - Install shell aliases for AI Toolkit commands

main() {
  set -euo pipefail

  local alias_file="${HOME}/.ai-toolkit-aliases"

  cat > "$alias_file" << 'EOF'
# AI Toolkit - shell aliases
# Source this file in your .bashrc / .zshrc:
#   [ -f ~/.ai-toolkit-aliases ] && source ~/.ai-toolkit-aliases

alias ai-mcp='install-mcp-servers'
alias ai-skills='install-skills'
alias ai-tookit='ai-toolkit'
alias ai-quality='check-code-quality'

# systemd user service shortcuts
alias ai-mcp-status='systemctl --user status ai-mcp-servers.service'
alias ai-mcp-run='systemctl --user start ai-mcp-servers.service'
alias ai-skills-status='systemctl --user status ai-skills.service'
alias ai-skills-run='systemctl --user start ai-skills.service'
alias ai-timers='systemctl --user list-timers "ai-*"'
EOF

  echo "Aliases written to $alias_file"
  echo ""
  echo "To activate, add this line to your shell rc file:"
  echo "  [ -f ~/.ai-toolkit-aliases ] && source ~/.ai-toolkit-aliases"
}

main "$@"
