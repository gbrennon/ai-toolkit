"""Install Pi Config — sync CLINE_API_KEY and register Cline provider."""

import json
import sys
from pathlib import Path

from ai_toolkit.shared_kernel.dotenv import load_dotenv

PI_AUTH_PATH: Path = Path.home() / ".pi" / "agent" / "auth.json"
PI_MODELS_PATH: Path = Path.home() / ".pi" / "agent" / "models.json"
OPENCODE_CONFIG_PATH: Path = Path.home() / ".config" / "opencode" / "opencode.json"


_CLINE_MODELS_PI: list[dict] = [
    {
        "id": "claude-sonnet-4-20250514",
        "name": "Claude Sonnet 4",
        "contextWindow": 200000,
        "maxTokens": 8192,
        "reasoning": True,
        "input": ["text", "image"],
        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
    },
    {
        "id": "claude-opus-4-20250514",
        "name": "Claude Opus 4",
        "contextWindow": 200000,
        "maxTokens": 8192,
        "reasoning": True,
        "input": ["text", "image"],
        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
    },
    {
        "id": "claude-haiku-3-5-20241022",
        "name": "Claude Haiku 3.5",
        "contextWindow": 200000,
        "maxTokens": 8192,
        "reasoning": False,
        "input": ["text", "image"],
        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
    },
]

_CLINE_PROVIDER_PI: dict = {
    "baseUrl": "https://api.anthropic.com",
    "api": "anthropic-messages",
    "apiKey": "CLINE_API_KEY",
    "models": _CLINE_MODELS_PI,
}


def _merge_json(file_path: Path, key: str, entry_key: str, entry: dict) -> bool:
    """Read *file_path* JSON, merge *entry* under top-level *key*[*entry_key*],
    and write back.  Returns True on success."""
    data: dict = {}
    if file_path.is_file():
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"Warning: {file_path} is invalid JSON, starting fresh")

    data.setdefault(key, {})[entry_key] = entry

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"  Cline provider registered in {file_path}")
    return True


def _sync_auth(auth_file: Path, api_key: str) -> bool:
    """Write the cline API key into Pi's auth.json."""
    auth_data: dict = {}
    if auth_file.is_file():
        try:
            auth_data = json.loads(auth_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"Warning: {auth_file} is invalid JSON, starting fresh")

    auth_data["cline"] = {"type": "api_key", "key": api_key}

    auth_file.parent.mkdir(parents=True, exist_ok=True)
    auth_file.write_text(
        json.dumps(auth_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"  CLINE_API_KEY written to {auth_file}")
    return True


def _register_pi_provider(models_path: Path, base_url: str) -> bool:
    """Add the Cline provider to Pi's models.json."""
    provider = dict(_CLINE_PROVIDER_PI)
    if base_url:
        provider["baseUrl"] = base_url
    return _merge_json(models_path, "providers", "Cline", provider)


def _register_opencode_provider(config_path: Path, base_url: str) -> bool:
    """Add the Cline provider to OpenCode's opencode.json."""
    opts: dict = {
        "baseURL": base_url or "https://api.anthropic.com/v1",
        "apiKey": "{env:CLINE_API_KEY}",
    }
    entry = {
        "npm": "@ai-sdk/anthropic",
        "name": "Cline",
        "options": opts,
        "models": {
            "claude-sonnet-4-20250514": {
                "name": "Claude Sonnet 4",
                "limit": {"context": 200000, "output": 8192},
            },
            "claude-opus-4-20250514": {
                "name": "Claude Opus 4",
                "limit": {"context": 200000, "output": 8192},
            },
            "claude-haiku-3-5-20241022": {
                "name": "Claude Haiku 3.5",
                "limit": {"context": 200000, "output": 8192},
            },
        },
    }
    nvidia_entry = {
        "npm": "@ai-sdk/openai-compatible",
        "name": "NVIDIA NIM",
        "options": {
            "baseURL": "https://integrate.api.nvidia.com/v1",
            "apiKey": "{env:NVIDIA_API_KEY}",
        },
        "models": {
            "nemotron-3-nano-30b-a3b": {"name": "Nemotron Nano 30B"},
            "nemotron-3-ultra-550b-a55b": {"name": "Nemotron Ultra 550B"},
            "google/gemma-4-31b-it": {"name": "Gemma 4 31B IT"},
        },
    }
    ok = _merge_json(config_path, "provider", "Cline", entry)
    ok = _merge_json(config_path, "provider", "nvidia", nvidia_entry) and ok
    return ok


def main(
    dotenv_path: Path | None = None,
    auth_path: Path | None = None,
    pi_models_path: Path | None = None,
    opencode_config_path: Path | None = None,
) -> int:
    """Sync CLINE_API_KEY and register Cline provider in Pi + OpenCode."""
    dotenv = dotenv_path or Path(".env")
    auth_file = auth_path or PI_AUTH_PATH
    pi_models = pi_models_path or PI_MODELS_PATH
    opencode_config = opencode_config_path or OPENCODE_CONFIG_PATH

    dotenv_vars: dict[str, str] = {}
    if dotenv.is_file():
        dotenv_vars = load_dotenv(dotenv)

    api_key = dotenv_vars.get("CLINE_API_KEY")
    base_url = dotenv_vars.get("CLINE_API_BASE_URL", "")

    if not api_key:
        print("CLINE_API_KEY not found in .env file — registering provider without auth (set CLINE_API_KEY to enable)")
        _register_pi_provider(pi_models, base_url)
        _register_opencode_provider(opencode_config, base_url)
        return 0

    errors: list[str] = []

    if not _sync_auth(auth_file, api_key):
        errors.append("Failed to write Pi auth.json")

    if not _register_pi_provider(pi_models, base_url):
        errors.append("Failed to register Cline in Pi models.json")

    if not _register_opencode_provider(opencode_config, base_url):
        errors.append("Failed to register Cline in OpenCode opencode.json")

    if errors:
        for err in errors:
            print(err)
        return 1

    print("\nCline provider registered for Pi and OpenCode.")
    print("  Models: claude-sonnet-4, claude-opus-4, claude-haiku-3.5")
    if base_url:
        print(f"  Base URL: {base_url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
