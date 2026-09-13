.DEFAULT_GOAL := help

PYTHON      := .venv/bin/python
UV          := uv
MCP_JSON    := mcp/mcp.json
DOTENV      := .env
TARGET_PATH := $(HOME)/.cline/data/settings/cline_mcp_settings.json

help:
	@grep -E '^[a-zA-Z0-9_-]+:' $(MAKEFILE_LIST) | cut -d: -f1 | sort | awk '{printf "  \033[36m%-28s\033[0m\n", $$1}'
	@echo ""
	@echo "  make install   runs all install targets"
	@echo "  make help      show this help"

setup:
	$(UV) sync

install-mcp:
	$(UV) run install-mcp-servers

install-skills:
	$(UV) run install-skills

install-agent-rules:
	$(UV) run install-agent-rules

install-omp-commands:
	$(UV) run install-omp-commands

install-provider-blocks:
	$(UV) run install-provider-blocks

install-quality-cli:
	mkdir -p $(HOME)/.local/bin $(HOME)/.config/ai-toolkit/semgrep
	install -m 755 scripts/check-code-quality.sh $(HOME)/.local/bin/check-code-quality
	cp -r rules/semgrep/* $(HOME)/.config/ai-toolkit/semgrep/

HOOK_AGENT ?= all

install-hooks:
	$(UV) run install-hooks --agent $(HOOK_AGENT)

install: install-mcp install-skills install-agent-rules install-omp-commands install-provider-blocks install-pi-config install-quality-cli install-hooks

install-pi-config:
	$(UV) run install-pi-config

deploy-mcp:
	$(UV) run install-mcp-servers

install-systemd:
	bash scripts/install-systemd.sh

uninstall-systemd:
	-systemctl --user disable --now gb-mcp-servers.timer 2>/dev/null
	-systemctl --user disable --now gb-skills.timer 2>/dev/null
	-rm -f $(HOME)/.config/systemd/user/gb-mcp-servers.*
	-rm -f $(HOME)/.config/systemd/user/gb-skills.*
	systemctl --user daemon-reload

install-aliases:
	bash scripts/install-aliases.sh

test:
	$(UV) run pytest tests/ --tb=short

test-unit:
	$(UV) run pytest tests/ -m unit --tb=short

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
	find . -type d -name '.pytest_cache' -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov/ dist/ build/ *.egg-info/
