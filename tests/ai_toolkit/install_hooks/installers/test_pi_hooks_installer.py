import json
from pathlib import Path

import pytest

from ai_toolkit.install_hooks.installers.pi_hooks_installer import (
    CODE_EXTENSIONS,
    HOOK_MATCHER,
    HOOK_PACKAGE,
    LEGACY_NOTIFICATION_CMD,
    PI_NOTIFICATION_EXTENSION_CONTENT,
    PiHooksInstaller,
    install_hooks,
)

pytestmark = pytest.mark.integration


def _expected_tool_conditions() -> set[str]:
    return {
        f"{tool}(*.{extension})"
        for tool in ("Write", "Edit")
        for extension in CODE_EXTENSIONS
    }


class TestPiHooksInstaller:
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

    def test_install_writes_quality_hook_and_notification_extension(
        self,
        tmp_path: Path,
    ) -> None:
        settings_target = tmp_path / "settings.json"
        extension_target = tmp_path / "extensions" / "ai-toolkit-notify.ts"

        installed = PiHooksInstaller.create(settings_target, extension_target).install()

        assert installed is True
        data = json.loads(settings_target.read_text(encoding="utf-8"))
        groups = data["hooks"]["PostToolUse"]
        assert len(groups) == 1
        assert groups[0]["matcher"] == HOOK_MATCHER
        hooks = groups[0]["hooks"]
        conditions = {hook["if"] for hook in hooks}
        assert conditions == _expected_tool_conditions()
        assert all(
            hook["type"] == "command"
            and hook["command"] == "check-modified-code-quality"
            for hook in hooks
        )
        assert HOOK_PACKAGE in data["packages"]
        assert extension_target.read_text(encoding="utf-8") == (
            PI_NOTIFICATION_EXTENSION_CONTENT
        )

    @staticmethod
    def test_notification_extension_uses_supported_lifecycle_boundaries() -> None:
        content = PI_NOTIFICATION_EXTENSION_CONTENT

        assert 'pi.on("ui_prompt_start"' in content
        assert 'pi.on("agent_before_settle"' in content
        assert 'pi.on("agent_settled"' in content
        assert 'pi.on("agent_error"' not in content
        assert 'pi.on("agent_end"' not in content
        assert '"agent-notify"' in content
        assert "window_index" not in content

    def test_install_removes_legacy_stop_notification_only(
        self,
        tmp_path: Path,
    ) -> None:
        target = tmp_path / "settings.json"
        target.write_text(
            json.dumps(
                {
                    "hooks": {
                        "Stop": [
                            {"hooks": [{"command": LEGACY_NOTIFICATION_CMD}]},
                            {"hooks": [{"command": "keep-this-hook"}]},
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )

        PiHooksInstaller.create(target).install()

        data = json.loads(target.read_text(encoding="utf-8"))
        assert data["hooks"]["Stop"] == [{"hooks": [{"command": "keep-this-hook"}]}]

    def test_install_merges_without_clobbering_existing(self, tmp_path: Path) -> None:
        target = tmp_path / "settings.json"
        target.write_text(json.dumps({"theme": "dark"}), encoding="utf-8")

        installed = PiHooksInstaller.create(target).install()

        assert installed is True
        data = json.loads(target.read_text(encoding="utf-8"))
        assert data["theme"] == "dark"
        assert HOOK_PACKAGE in data["packages"]

    def test_install_does_not_duplicate_package(self, tmp_path: Path) -> None:
        target = tmp_path / "settings.json"
        target.write_text(json.dumps({"packages": [HOOK_PACKAGE]}), encoding="utf-8")

        PiHooksInstaller.create(target).install()

        data = json.loads(target.read_text(encoding="utf-8"))
        assert data["packages"].count(HOOK_PACKAGE) == 1

    def test_install_replaces_existing_quality_hook_config(
        self, tmp_path: Path
    ) -> None:
        target = tmp_path / "settings.json"
        target.write_text(
            json.dumps({"hooks": {"PostToolUse": [{}]}}),
            encoding="utf-8",
        )

        PiHooksInstaller.create(target).install()

        data = json.loads(target.read_text(encoding="utf-8"))
        assert len(data["hooks"]["PostToolUse"]) == 1
        assert data["hooks"]["PostToolUse"][0]["matcher"] == HOOK_MATCHER

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
        target1 = tmp_path / "settings1.json"
        target2 = tmp_path / "settings2.json"

        PiHooksInstaller.create(target1).install()
        first_content = target1.read_text(encoding="utf-8")
        PiHooksInstaller.create(target2).install()
        second_content = target2.read_text(encoding="utf-8")

        assert first_content == second_content
