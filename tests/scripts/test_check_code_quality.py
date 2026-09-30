import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[2] / "scripts" / "check-code-quality.sh"


def create_fake_tools(workspace: Path) -> Path:
    bin_dir = workspace / "bin"
    bin_dir.mkdir()
    lizard = bin_dir / "lizard"
    lizard.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    semgrep = bin_dir / "semgrep"
    semgrep.write_text(
        "#!/bin/sh\nprintf '%s\\n' \"$@\" > semgrep-args.txt\nexit 0\n",
        encoding="utf-8",
    )
    lizard.chmod(0o755)
    semgrep.chmod(0o755)
    return bin_dir


def run_quality_check(
    workspace: Path, bin_dir: Path, relative_source: str
) -> list[str]:
    result = subprocess.run(
        [str(SCRIPT), relative_source],
        cwd=workspace,
        env={
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "HOME": str(workspace / "home"),
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    return (workspace / "semgrep-args.txt").read_text(encoding="utf-8").splitlines()


@pytest.mark.parametrize(
    ("filename", "contents"),
    [("example.rs", "fn main() {}\n"), ("example.py", "def main(): pass\n")],
)
def test_single_workspace_uses_its_semgrep_config(
    tmp_path: Path, filename: str, contents: str
) -> None:
    source = tmp_path / "src" / filename
    source.parent.mkdir()
    source.write_text(contents, encoding="utf-8")
    config = tmp_path / ".semgrep"
    config.mkdir()
    nested_rules = config / "language" / "workspace.yaml"
    nested_rules.parent.mkdir()
    nested_rules.write_text("rules: []\n", encoding="utf-8")
    global_rules = tmp_path / "home" / ".config" / "ai-toolkit" / "semgrep"
    global_rules.mkdir(parents=True)
    (global_rules / "fallback.yml").write_text("rules: []\n", encoding="utf-8")
    bin_dir = create_fake_tools(tmp_path)

    arguments = run_quality_check(tmp_path, bin_dir, f"src/{filename}")

    assert arguments[arguments.index("--config") + 1] == str(config)
    assert arguments[-1] == f"src/{filename}"


def test_multiple_workspaces_use_their_own_semgrep_config(tmp_path: Path) -> None:
    workspaces = [tmp_path / "rust-project", tmp_path / "python-project"]
    sources = [("src/main.rs", "fn main() {}\n"), ("src/main.py", "def main(): pass\n")]
    selected_configs: list[str] = []

    for workspace, (relative_source, contents) in zip(workspaces, sources, strict=True):
        source = workspace / relative_source
        source.parent.mkdir(parents=True)
        source.write_text(contents, encoding="utf-8")
        config = workspace / ".semgrep"
        config.mkdir()
        nested_rules = config / "language" / "project.yaml"
        nested_rules.parent.mkdir()
        nested_rules.write_text("rules: []\n", encoding="utf-8")
        bin_dir = create_fake_tools(workspace)

        arguments = run_quality_check(workspace, bin_dir, relative_source)
        selected_configs.append(arguments[arguments.index("--config") + 1])

    assert selected_configs == [str(workspace / ".semgrep") for workspace in workspaces]
