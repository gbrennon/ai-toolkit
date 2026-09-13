"""Install Provider Blocks — allow OpenAI & Anthropic providers on OMP, Cline, and Pi.

Ensures OpenAI and Anthropic access is allowed on all agents by:
  - Removing from disabledProviders in ~/.omp/agent/models.yml       (OMP)
  - Removing from disabledProviders in ~/.pi/agent/models.json       (Pi)
  - Ensuring provider entries are not removed from Cline providers.json (Cline)
"""

import json
import sys
from pathlib import Path

import yaml

OMP_MODELS_PATH = Path.home() / ".omp" / "agent" / "models.yml"
CLINE_PROVIDERS_PATH = Path.home() / ".cline" / "data" / "settings" / "providers.json"
PI_MODELS_PATH = Path.home() / ".pi" / "agent" / "models.json"

_ALLOWED_PROVIDERS = ("openai", "anthropic")
_BLOCKED_PROVIDERS = _ALLOWED_PROVIDERS


def _read_yaml(path: Path) -> dict:
    """Read and parse a YAML file. Returns empty dict if missing or invalid."""
    if not path.is_file():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        print(f"Warning: {path} is invalid YAML, starting fresh")
        return {}


def _write_yaml(path: Path, data: dict) -> bool:
    """Write data as YAML to path. Creates directories as needed."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.dump(data, default_flow_style=False, allow_unicode=True),
            encoding="utf-8",
        )
        return True
    except OSError as e:
        print(f"Error writing {path}: {e}", file=sys.stderr)
        return False


def _read_json(path: Path) -> dict:
    """Read and parse a JSON file. Returns empty dict if missing or invalid."""
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"Warning: {path} is invalid JSON, starting fresh")
        return {}


def _write_json(path: Path, data: dict) -> bool:
    """Write data as JSON to path. Creates directories as needed."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return True
    except OSError as e:
        print(f"Error writing {path}: {e}", file=sys.stderr)
        return False


def _allow_omp_providers(models_path: Path) -> bool:
    """Allow OpenAI and Anthropic in OMP by removing them from disabledProviders."""
    try:
        data = _read_yaml(models_path)
        disabled: list[str] = data.get("disabledProviders", [])
        newly_allowed: list[str] = [p for p in _ALLOWED_PROVIDERS if p in disabled]
        if newly_allowed:
            data["disabledProviders"] = [p for p in disabled if p not in _ALLOWED_PROVIDERS]
            print(f"  OMP: allowed {', '.join(newly_allowed)}")
        else:
            print("  OMP: openai + anthropic already allowed")
        return _write_yaml(models_path, data)
    except Exception as e:
        print(f"Error updating OMP models.yml: {e}", file=sys.stderr)
        return False


def _allow_pi_providers(models_path: Path) -> bool:
    """Allow OpenAI and Anthropic in Pi by removing them from disabledProviders."""
    try:
        data = _read_json(models_path)
        if not data:
            print("  Pi: no models.json found, nothing to allow")
            return True
        disabled: list[str] = data.get("disabledProviders", [])
        if not disabled:
            print("  Pi: openai + anthropic already allowed")
            return True
        newly_allowed = [p for p in _ALLOWED_PROVIDERS if p in disabled]
        if newly_allowed:
            data["disabledProviders"] = [p for p in disabled if p not in _ALLOWED_PROVIDERS]
            print(f"  Pi: allowed {', '.join(newly_allowed)}")
            return _write_json(models_path, data)
        print("  Pi: openai + anthropic already allowed")
        return True
    except Exception as e:
        print(f"Error updating Pi models.json: {e}", file=sys.stderr)
        return False


def _allow_cline_providers(providers_path: Path) -> bool:
    """Allow OpenAI and Anthropic in Cline — ensures they are not removed."""
    try:
        data = _read_json(providers_path)
        if not data:
            print("  Cline: no providers.json found, nothing to block — already allowed")
            return True
        print("  Cline: openai + anthropic allowed (no removal)")
        return True
    except Exception as e:
        print(f"Error checking Cline providers.json: {e}", file=sys.stderr)
        return False


def _block_omp_providers(models_path: Path) -> bool:
    return _allow_omp_providers(models_path)


def _block_cline_providers(providers_path: Path) -> bool:
    return _allow_cline_providers(providers_path)


def install(
    omp_models_path: Path | None = None,
    cline_providers_path: Path | None = None,
    pi_models_path: Path | None = None,
) -> int:
    """Allow OpenAI and Anthropic providers on OMP, Cline, and Pi."""
    omp_models = omp_models_path or OMP_MODELS_PATH
    cline_providers = cline_providers_path or CLINE_PROVIDERS_PATH
    pi_models = pi_models_path or PI_MODELS_PATH

    print("\nAllowing OpenAI and Anthropic providers...")
    errors: list[str] = []

    if not _allow_omp_providers(omp_models):
        errors.append("Failed to allow OMP providers")

    if not _allow_cline_providers(cline_providers):
        errors.append("Failed to allow Cline providers")

    if not _allow_pi_providers(pi_models):
        errors.append("Failed to allow Pi providers")

    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 1

    print("\nDone. OpenAI and Anthropic are now allowed on OMP, Cline, and Pi.")
    return 0


def main() -> int:
    return install()


if __name__ == "__main__":
    sys.exit(main())
