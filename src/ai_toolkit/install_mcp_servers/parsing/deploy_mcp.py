import json
import os
from pathlib import Path

from jinja2 import Environment

from ai_toolkit.install_mcp_servers.models.agent_platform import AgentPlatform
from ai_toolkit.shared_kernel.dotenv import load_dotenv


def agent_target_path(platform: AgentPlatform) -> Path:
    """Return the absolute config path for a given agent platform."""
    return Path.home() / platform.config_path


def _filter_servers_for_agent(servers: dict, agent: AgentPlatform | str) -> dict:
    """Filter mcpServers dict to only include entries relevant to *agent*.

    Rules:
    - Servers with no ``platform`` are shared — included everywhere.
    - Servers with ``platform == agent`` are included for that agent.
    - Servers with a different platform are excluded.
    """
    agent_value = agent.value if isinstance(agent, AgentPlatform) else agent
    filtered: dict = {}
    for name, cfg in servers.items():
        platform = cfg.get("platform")
        if platform is None:
            filtered[name] = cfg
        elif platform == agent_value:
            filtered[name] = cfg

    return filtered


def deploy_mcp(
    source_path: Path,
    target_path: Path,
    dotenv_path: Path | None = None,
    *,
    agent_targets: dict[AgentPlatform, Path] | None = None,
) -> bool:
    """Render ``source_path`` with Jinja2 and write to ``target_path``.

    If *agent_targets* is provided, additionally write filtered configs
    to each agent's target path so that servers are scoped to the right tool.
    """
    if not source_path.exists():
        print(f"Source {source_path} not found")
        return False

    dotenv_vars: dict[str, str] = {}
    if dotenv_path and dotenv_path.is_file():
        dotenv_vars = load_dotenv(dotenv_path)

    template_context = dict(os.environ)
    template_context.update(dotenv_vars)

    template_source = source_path.read_text(encoding="utf-8")
    env = Environment()
    rendered = env.from_string(template_source).render(template_context)

    try:
        raw = json.loads(rendered)
    except json.JSONDecodeError as e:
        print(f"Failed to parse rendered template as JSON: {e}")
        return False

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(
        json.dumps(raw, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Deployed MCP config to {target_path}")

    if agent_targets:
        servers = raw.get("mcpServers", {})

        for agent, agent_path in agent_targets.items():
            filtered_servers = _filter_servers_for_agent(servers, agent)
            agent_config: dict = {**raw}
            agent_config["mcpServers"] = filtered_servers

            agent_path.parent.mkdir(parents=True, exist_ok=True)
            agent_path.write_text(
                json.dumps(agent_config, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            print(f"Deployed MCP config for {agent.value} to {agent_path}")

    return True
