import argparse
import json
import sys
from pathlib import Path

AGENTS = ("pi", "opencode", "cline", "omp", "all")
PI_SETTINGS = Path.home() / ".pi" / "agent" / "settings.json"
OPENCODE_CONFIG = Path.home() / ".config" / "opencode" / "opencode.json"

HOOK_CMD = "check-code-quality 2>&1 | head -120"

def _install_pi() -> bool:
    try:
        data = {}
        if PI_SETTINGS.is_file():
            data = json.loads(PI_SETTINGS.read_text(encoding="utf-8"))
        data.setdefault("hooks", {})["PostToolUse"] = [
            {"matcher": "write|edit|bash", "hooks": [{"type": "command", "command": HOOK_CMD}]}
        ]
        pkg = "@hsingjui/pi-hooks"
        pkgs = data.setdefault("packages", [])
        if pkg not in pkgs:
            pkgs.append(pkg)
        PI_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
        PI_SETTINGS.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"  Pi: PostToolUse hook installed in {PI_SETTINGS}")
        return True
    except Exception as e:
        print(f"Pi hook failed: {e}", file=sys.stderr)
        return False

def _install_opencode(agent: str) -> bool:
    print(f"  {agent}: hooks via native AGENTS.md enforcement (no pi-hooks needed)")
    return True


MAP = {"pi": _install_pi}

def install(agent: str) -> int:
    print(f"\nInstalling hooks for: {agent}")
    if agent == "all":
        ok = _install_pi()
        for other in ("opencode", "cline", "omp"):
            ok = _install_opencode(other) and ok
        return 0 if ok else 1
    if agent == "pi":
        return 0 if _install_pi() else 1
    return 0 if _install_opencode(agent) else 1

def main() -> int:
    p = argparse.ArgumentParser(description="Install quality hooks per agent")
    p.add_argument("--agent", choices=AGENTS, default="all", help="which agent to configure")
    args = p.parse_args()
    return install(args.agent)

if __name__ == "__main__":
    sys.exit(main())
