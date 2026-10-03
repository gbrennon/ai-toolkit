# AI Agent Skill Library

Curated skills for AI coding agents: architecture patterns (Clean, Hexagonal, CQRS, Event-driven) and testing strategies (Unit, Integration, E2E).

Each skill is a reusable prompt fragment that teaches an agent a specific practice.

## Quick Start

```bash
uv sync                    # install dependencies
make install-cli           # install the ai-toolkit CLI onto PATH
make install-mcp           # install & deploy MCP servers
make install-skills        # install skills
make install               # install everything
```

## Make Targets

| Command | Description |
|---------|-------------|
| `make setup` | Install dependencies (`uv sync`) |
| `make install-cli` | Install the `ai-toolkit` CLI into the active Python environment |
| `make install-mcp` | Install MCP servers from `mcp/mcp.json` and deploy to all agents |
| `make install-skills` | Install skills |
| `make install-agent-rules` | Compose `agent_rules/` into every AGENTS.md target listed in the manifest |
| `make install` | Install everything (cli + mcp + skills + rules + hooks) |
| `make deploy-mcp` | Same as `install-mcp` — install + deploy to all agents |
| `make test` | Run all tests |
| `make test-unit` | Run unit tests only |
| `make clean` | Remove build artifacts and caches |
| `make help` | Show available targets |

## MCP Servers

MCP (Model Context Protocol) servers are configured in `mcp/mcp.json`. On install, each server's runtime is verified (npx, uvx, or custom command) and its config is deployed to every supported agent platform.

### Supported agent platforms

| Agent | Config path |
|-------|-------------|
| Cline (default) | `~/.cline/data/settings/cline_mcp_settings.json` |
| OpenCode | `~/.config/opencode/mcp.json` |
| Pi | `~/.config/pi/mcp.json` |
| Vibe | `~/.config/vibe/mcp.json` |

### Platform-scoped servers

Add a `"platform"` field to restrict a server to a single agent:

```json
{
  "mcpServers": {
    "my-opencode-tool": {
      "command": "npx",
      "args": ["-y", "some-package"],
      "platform": "opencode"
    }
  }
}
```

Servers **without** a `platform` are shared — deployed to every agent. Servers **with** a `platform` only go to that agent's config.

See [docs/mcp-servers.md](docs/mcp-servers.md) for full details on the config format, server fields, multi-agent deployment, and adding new agent platforms ([guide](docs/adding-agent-platforms.md)).

## Configuration

Place secrets in `.env`:

```
GITHUB_TOKEN=...
FORGEJO_ACCESS_TOKEN=...
```

The `mcp/mcp.json` template uses Jinja2 expressions — missing variables fall back to human-readable placeholders.

## Documentation

| Document | Description |
|----------|-------------|
| [docs/mcp-servers.md](docs/mcp-servers.md) | Full MCP server config reference: fields, deployment, platform scoping |
| [docs/adding-agent-platforms.md](docs/adding-agent-platforms.md) | Step-by-step guide to add a new agent platform |
| [docs/authoring-agent-rules.md](docs/authoring-agent-rules.md) | How to add and improve the rule files composed into AGENTS.md |
