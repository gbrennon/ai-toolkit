import os
import shutil
import subprocess
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parents[2] / "scripts"
SCRIPT_NAMES = (
    "check-code-quality.sh",
    "install-aliases.sh",
    "install-systemd.sh",
    "install_cline_rules.sh",
)


class TestShellScripts:
    """Verify shell scripts in scripts/ obey formatting and entry-point rules."""

    @staticmethod
    def _scripts() -> list[Path]:
        return [SCRIPTS_DIR / name for name in SCRIPT_NAMES]

    @staticmethod
    def _top_level_prefix(script: Path) -> str:
        lines = script.read_text(encoding="utf-8").splitlines()
        prefix: list[str] = []
        for line in lines:
            if (
                line
                and not line.startswith(("#", " ", "\t"))
                and line.endswith("() {")
            ):
                break
            prefix.append(line)
        return "\n".join(prefix)

    @staticmethod
    def _run_script(
        script: Path,
        *,
        input_text: str = "",
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        merged_env = dict(os.environ)
        if env is not None:
            merged_env.update(env)
        return subprocess.run(
            ["bash", str(script)],
            input=input_text,
            capture_output=True,
            text=True,
            check=False,
            env=merged_env,
        )

    def test_scripts_are_ascii_only(self) -> None:
        for script in self._scripts():
            script.read_text(encoding="ascii")

    def test_scripts_have_main_entry_point(self) -> None:
        for script in self._scripts():
            text = script.read_text(encoding="ascii")
            assert "main()" in text
            assert text.rstrip().endswith('main "$@"')

    def test_scripts_do_not_execute_setup_at_file_scope(self) -> None:
        forbidden = ("set -e", '="', "=(")
        for script in self._scripts():
            prefix = self._top_level_prefix(script)
            assert not any(statement in prefix for statement in forbidden), script

    def test_install_aliases_writes_alias_file(self, tmp_path: Path) -> None:
        result = self._run_script(
            SCRIPTS_DIR / "install-aliases.sh",
            env={"HOME": str(tmp_path)},
        )

        assert result.returncode == 0
        aliases = (tmp_path / ".ai-toolkit-aliases").read_text(encoding="ascii")
        assert "alias ai-quality='check-code-quality'" in aliases

    def test_install_systemd_copies_units_and_starts_timers(
        self,
        tmp_path: Path,
    ) -> None:
        repo = tmp_path / "repo"
        scripts_dir = repo / "scripts"
        systemd_dir = repo / "systemd"
        bin_dir = tmp_path / "bin"
        scripts_dir.mkdir(parents=True)
        systemd_dir.mkdir()
        bin_dir.mkdir()
        shutil.copy2(
            SCRIPTS_DIR / "install-systemd.sh",
            scripts_dir / "install-systemd.sh",
        )
        (systemd_dir / "example.timer").write_text("[Timer]\n", encoding="ascii")
        systemctl_log = tmp_path / "systemctl.log"
        systemctl = bin_dir / "systemctl"
        systemctl.write_text(
            f'#!/usr/bin/env bash\nprintf \'%s\\n\' "$*" >> {systemctl_log}\n',
            encoding="ascii",
        )
        systemctl.chmod(0o755)

        result = self._run_script(
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

    def test_install_cline_rules_moves_current_rule_files(
        self,
        tmp_path: Path,
    ) -> None:
        repo = tmp_path / "repo"
        scripts_dir = repo / "scripts"
        rules_dir = repo / "agent_rules"
        scripts_dir.mkdir(parents=True)
        rules_dir.mkdir()
        shutil.copy2(
            SCRIPTS_DIR / "install_cline_rules.sh",
            scripts_dir / "install_cline_rules.sh",
        )
        rule_names = (
            "00-global-noise-exclusions.md",
            "01-general-project-policies.md",
            "02-architecture-guidance.md",
        )
        for name in rule_names:
            (rules_dir / name).write_text(name, encoding="ascii")

        result = self._run_script(
            scripts_dir / "install_cline_rules.sh",
            env={"HOME": str(tmp_path / "home")},
        )

        assert result.returncode == 0
        for name in rule_names:
            installed_rule = tmp_path / "home/.cline/rules" / name
            assert installed_rule.read_text(encoding="ascii") == name
