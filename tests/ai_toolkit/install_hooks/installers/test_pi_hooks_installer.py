import json
import os
import subprocess
from pathlib import Path

import pytest

from ai_toolkit.install_hooks.installers.pi_hooks_installer import (
    HOOK_PACKAGE,
    LEGACY_NOTIFICATION_CMD,
    LEGACY_QUALITY_CMD,
    NPM_HOOK_PACKAGE,
    PI_NOTIFICATION_EXTENSION_CONTENT,
    PI_QUALITY_EXTENSION_CONTENT,
    PiHooksInstaller,
    install_hooks,
)

pytestmark = pytest.mark.integration


class TestPiHooksInstaller:
    """Verify PiHooksInstaller writes native TS extensions and cleans legacy hooks."""

    def test_install_hooks_copies_hook_from_package_path(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        assert install_hooks() is True

        installed_hook = tmp_path / ".hooks" / "pr_opened_hook.py"
        assert installed_hook.is_file()
        assert "class PROpenedHook" in installed_hook.read_text(encoding="utf-8")

    def test_install_writes_native_quality_and_notification_extensions(
        self,
        tmp_path: Path,
    ) -> None:
        settings_target = tmp_path / "settings.json"
        notify_target = tmp_path / "extensions" / "ai-toolkit-notify.ts"
        quality_target = tmp_path / "extensions" / "ai-toolkit-quality.ts"

        installed = PiHooksInstaller.create(
            settings_target,
            notify_target,
            quality_target,
        ).install()

        assert installed is True
        assert notify_target.read_text(encoding="utf-8") == (
            PI_NOTIFICATION_EXTENSION_CONTENT
        )
        assert quality_target.read_text(encoding="utf-8") == (
            PI_QUALITY_EXTENSION_CONTENT
        )
        data = json.loads(settings_target.read_text(encoding="utf-8"))
        assert "hooks" not in data
        assert "packages" not in data

    @staticmethod
    def test_extensions_use_supported_contracts_and_native_circuit_breaker() -> None:
        notify_content = PI_NOTIFICATION_EXTENSION_CONTENT
        quality_content = PI_QUALITY_EXTENSION_CONTENT

        assert 'pi.on("ui_prompt_start"' in notify_content
        assert 'pi.on("agent_before_settle"' in notify_content
        assert 'pi.on("agent_settled"' in notify_content
        assert '"agent-notify"' in notify_content
        assert 'pi.on("tool_result"' in quality_content
        assert "class CircuitBreakerStore" in quality_content
        assert '"check-code-quality"' in quality_content
        assert "check-modified-code-quality" not in quality_content

    def test_install_removes_legacy_stop_and_post_tool_use_hooks(
        self,
        tmp_path: Path,
    ) -> None:
        target = tmp_path / "settings.json"
        target.write_text(
            json.dumps(
                {
                    "packages": [HOOK_PACKAGE, NPM_HOOK_PACKAGE, "npm:keep-pkg"],
                    "hooks": {
                        "PostToolUse": [
                            {"hooks": [{"command": LEGACY_QUALITY_CMD}]},
                            {"hooks": [{"command": "keep-post-hook"}]},
                        ],
                        "Stop": [
                            {"hooks": [{"command": LEGACY_NOTIFICATION_CMD}]},
                            {"hooks": [{"command": "keep-this-hook"}]},
                        ],
                    },
                }
            ),
            encoding="utf-8",
        )

        PiHooksInstaller.create(target).install()

        data = json.loads(target.read_text(encoding="utf-8"))
        assert data["packages"] == ["npm:keep-pkg"]
        assert data["hooks"]["PostToolUse"] == [
            {"hooks": [{"command": "keep-post-hook"}]}
        ]
        assert data["hooks"]["Stop"] == [{"hooks": [{"command": "keep-this-hook"}]}]

    def test_install_merges_without_clobbering_existing(self, tmp_path: Path) -> None:
        target = tmp_path / "settings.json"
        target.write_text(json.dumps({"theme": "dark"}), encoding="utf-8")

        installed = PiHooksInstaller.create(target).install()

        assert installed is True
        data = json.loads(target.read_text(encoding="utf-8"))
        assert data == {"theme": "dark"}

    def test_installed_quality_extension_executes_under_bun_fake_hook_api(
        self, tmp_path: Path
    ) -> None:
        settings_target = tmp_path / "settings.json"
        notify_target = tmp_path / "extensions" / "ai-toolkit-notify.ts"
        quality_target = tmp_path / "extensions" / "ai-toolkit-quality.ts"
        PiHooksInstaller.create(settings_target, notify_target, quality_target).install()
        harness = tmp_path / "harness.mjs"
        harness.write_text(
            f'import hook from "{quality_target.as_posix()}";\n'
            'let h; const calls = [];\n'
            'hook({ on(_e, fn) { h = fn; }, async exec(c, a) {\n'
            '  calls.push(c); return { code: 1, stdout: "", stderr: "err" };\n'
            '} });\n'
            'const ev = { toolName: "write", input: { path: "a.py" }, content: [] };\n'
            'const ctx = { cwd: "/tmp", sessionId: "s1" };\n'
            'const p1 = await h(ev, ctx); const p2 = await h(ev, ctx);\n'
            'console.log(JSON.stringify({ calls: calls.length, p1, p2 }));\n',
            encoding="utf-8",
        )
        env = {
            "PATH": os.environ.get("PATH", ""),
            "AI_TOOLKIT_CIRCUIT_BREAKER_STATE": str(tmp_path / "breaker.json"),
            "AI_TOOLKIT_CIRCUIT_BREAKER_THRESHOLD": "2",
        }

        result = subprocess.run(
            ["bun", str(harness)], cwd="/tmp", capture_output=True, text=True, check=False, env=env
        )

        assert result.returncode == 0
        payload = json.loads(result.stdout.strip())
        assert payload["calls"] == 2
        assert "circuit_breaker_open" in json.dumps(payload["p2"])

    def test_install_returns_false_when_write_fails(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        target = tmp_path / "settings.json"
        target.mkdir()

        installed = PiHooksInstaller.create(target).install()

        assert installed is False
        assert "Pi hook failed" in capsys.readouterr().err

    def test_install_is_deterministic(self, tmp_path: Path) -> None:
        target1 = tmp_path / "dir1" / "settings.json"
        target2 = tmp_path / "dir2" / "settings.json"

        PiHooksInstaller.create(target1).install()
        first_content = target1.read_text(encoding="utf-8")
        PiHooksInstaller.create(target2).install()
        second_content = target2.read_text(encoding="utf-8")

        assert first_content == second_content
