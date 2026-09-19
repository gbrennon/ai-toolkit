import os
import shutil
import subprocess
from pathlib import Path


SCRIPTS_DIR = Path(__file__).parents[2] / "scripts"
SCRIPT_NAMES = (
    "check-code-quality.sh",
    "check-modified-code-quality.sh",
    "install-aliases.sh",
    "install-systemd.sh",
    "install_cline_rules.sh",
)


def scripts() -> list[Path]:
    return [SCRIPTS_DIR / name for name in SCRIPT_NAMES]


def top_level_prefix(script: Path) -> str:
    lines = script.read_text(encoding="utf-8").splitlines()
    prefix: list[str] = []
    for line in lines:
        if line and not line.startswith(("#", " ", "\t")) and line.endswith("() {"):
            break
        prefix.append(line)
    return "\n".join(prefix)


def test_scripts_are_ascii_only() -> None:
    for script in scripts():
        script.read_text(encoding="ascii")


def test_scripts_have_main_entry_point() -> None:
    for script in scripts():
        text = script.read_text(encoding="ascii")
        assert "main()" in text
        assert text.rstrip().endswith('main "$@"')


def test_scripts_do_not_execute_setup_at_file_scope() -> None:
    forbidden = ("set -e", "=\"", "=(")
    for script in scripts():
        prefix = top_level_prefix(script)
        assert not any(statement in prefix for statement in forbidden), script


def run_script(script: Path, *, input_text: str = "", env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(script)],
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, **(env or {})},
    )


def test_install_aliases_writes_alias_file(tmp_path: Path) -> None:
    result = run_script(SCRIPTS_DIR / "install-aliases.sh", env={"HOME": str(tmp_path)})

    assert result.returncode == 0
    aliases = (tmp_path / ".ai-toolkit-aliases").read_text(encoding="ascii")
    assert "alias ai-quality='check-code-quality'" in aliases


def test_install_systemd_copies_units_and_starts_timers(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    scripts_dir = repo / "scripts"
    systemd_dir = repo / "systemd"
    bin_dir = tmp_path / "bin"
    scripts_dir.mkdir(parents=True)
    systemd_dir.mkdir()
    bin_dir.mkdir()
    shutil.copy2(SCRIPTS_DIR / "install-systemd.sh", scripts_dir / "install-systemd.sh")
    (systemd_dir / "example.timer").write_text("[Timer]\n", encoding="ascii")
    systemctl_log = tmp_path / "systemctl.log"
    systemctl = bin_dir / "systemctl"
    systemctl.write_text(f"#!/usr/bin/env bash\nprintf '%s\\n' \"$*\" >> {systemctl_log}\n", encoding="ascii")
    systemctl.chmod(0o755)

    result = run_script(
        scripts_dir / "install-systemd.sh",
        env={
            "HOME": str(tmp_path / "home"),
            "XDG_CONFIG_HOME": str(tmp_path / "config"),
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
        },
    )

    assert result.returncode == 0
    assert (tmp_path / "config/systemd/user/example.timer").exists()
    assert systemctl_log.read_text(encoding="ascii").splitlines() == [
        "--user daemon-reload",
        "--user enable --now example.timer",
    ]


def test_install_cline_rules_moves_current_rule_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    scripts_dir = repo / "scripts"
    rules_dir = repo / "agent_rules"
    scripts_dir.mkdir(parents=True)
    rules_dir.mkdir()
    shutil.copy2(SCRIPTS_DIR / "install_cline_rules.sh", scripts_dir / "install_cline_rules.sh")
    for name in ("00-global-noise-exclusions.md", "01-general-project-policies.md", "02-architecture-guidance.md"):
        (rules_dir / name).write_text(name, encoding="ascii")

    result = run_script(scripts_dir / "install_cline_rules.sh", env={"HOME": str(tmp_path / "home")})

    assert result.returncode == 0
    for name in ("00-global-noise-exclusions.md", "01-general-project-policies.md", "02-architecture-guidance.md"):
        assert (tmp_path / "home/.cline/rules" / name).read_text(encoding="ascii") == name
