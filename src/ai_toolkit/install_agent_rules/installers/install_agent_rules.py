from pathlib import Path

from ai_toolkit.install_agent_rules.parsing.compose_rules import (
    compose_rules_content,
)
from ai_toolkit.install_agent_rules.parsing.load_rules_dir import (
    load_rules_entries,
    read_rules_dir,
)

_GLOBAL_RULES_DIR = Path.home() / ".config" / "ai-toolkit" / "rules.d"

AGENT_TARGETS_FILE = Path.home() / ".config" / "ai-toolkit" / "agent_targets.txt"

_DEFAULT_TARGETS_TEMPLATE = """\
~/.agents/AGENTS.md
~/.config/opencode/AGENTS.md
~/.omp/agent/AGENTS.md
~/.config/antigravity/AGENTS.md
~/.pi/agent/AGENTS.md
"""


def read_target_paths(manifest: Path) -> list[Path]:
    """Read destination paths from a manifest file, one path per line.

    Blank lines and lines starting with ``#`` are ignored. A leading ``~`` is
    expanded to the current user's home directory.
    """
    if not manifest.is_file():
        return []
    targets: list[Path] = []
    for raw in manifest.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        targets.append(Path(line).expanduser())
    return targets


def install_agent_rules(
    source_dir: Path | None = None,
    targets_file: Path | None = None,
    target_path: Path | None = None,
) -> int:
    rules_dir = source_dir or _GLOBAL_RULES_DIR

    files = read_rules_dir(rules_dir)
    if not files:
        print(f"No rules found in {rules_dir}")
        return 1

    manifest = targets_file or AGENT_TARGETS_FILE
    if targets_file is None and not manifest.is_file():
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(_DEFAULT_TARGETS_TEMPLATE, encoding="utf-8")
        print(
            f"Created default target manifest at {manifest}\n"
            f"  Edit it to match your installed agentic tools."
        )
    targets = read_target_paths(manifest)
    if target_path is not None:
        targets.append(target_path)

    seen: set[Path] = set()
    unique_targets = [t for t in targets if not (t in seen or seen.add(t))]
    if not unique_targets:
        print(f"No target paths found in {manifest}")
        return 1

    rules = load_rules_entries(files)
    content = compose_rules_content(rules, str(rules_dir))
    for target in unique_targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"Composed {len(rules)} rules into {target}")
    return 0
