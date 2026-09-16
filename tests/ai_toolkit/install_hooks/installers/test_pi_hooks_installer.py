import json

import pytest

from ai_toolkit.install_hooks.installers.pi_hooks_installer import (
    CODE_EXTENSIONS,
    HOOK_CMD,
    HOOK_MATCHER,
    HOOK_PACKAGE,
    PiHooksInstaller,
)

pytestmark = pytest.mark.integration


class TestPiHooksInstaller:
    def test_install_writes_hook_and_package_to_new_file(self, tmp_path):
        target = tmp_path / "settings.json"

        installed = PiHooksInstaller.create(target).install()

        assert installed is True
        data = json.loads(target.read_text(encoding="utf-8"))
        groups = data["hooks"]["PostToolUse"]
        assert len(groups) == 1
        assert groups[0]["matcher"] == HOOK_MATCHER
        hooks = groups[0]["hooks"]
        conditions = {hook["if"] for hook in hooks}
        expected_conditions = {
            f"{tool}(*.{ext})" for tool in ("Write", "Edit")
            for ext in CODE_EXTENSIONS
        }
        assert conditions == expected_conditions
        assert all(
            hook["type"] == "command"
            and hook["command"] == "check-modified-code-quality"
            for hook in hooks
        )
        assert HOOK_PACKAGE in data["packages"]

    def test_install_merges_without_clobbering_existing(self, tmp_path):
        target = tmp_path / "settings.json"
        target.write_text(json.dumps({"theme": "dark"}), encoding="utf-8")

        installed = PiHooksInstaller.create(target).install()

        assert installed is True
        data = json.loads(target.read_text(encoding="utf-8"))
        assert data["theme"] == "dark"
        assert HOOK_PACKAGE in data["packages"]

    def test_install_does_not_duplicate_package(self, tmp_path):
        target = tmp_path / "settings.json"
        target.write_text(
            json.dumps({"packages": [HOOK_PACKAGE]}), encoding="utf-8"
        )

        PiHooksInstaller.create(target).install()

        data = json.loads(target.read_text(encoding="utf-8"))
        assert data["packages"].count(HOOK_PACKAGE) == 1

    def test_install_replaces_existing_hook_config(self, tmp_path):
        target = tmp_path / "settings.json"
        target.write_text(
            json.dumps({"hooks": {"PostToolUse": [{}]}}), encoding="utf-8"
        )

        PiHooksInstaller.create(target).install()

        data = json.loads(target.read_text(encoding="utf-8"))
        assert len(data["hooks"]["PostToolUse"]) == 1
        assert data["hooks"]["PostToolUse"][0]["matcher"] == HOOK_MATCHER

    def test_install_returns_false_when_write_fails(self, tmp_path, capsys):
        target = tmp_path / "settings.json"
        target.mkdir()

        installed = PiHooksInstaller.create(target).install()

        assert installed is False
        assert "Pi hook failed" in capsys.readouterr().err

    def test_install_is_deterministic(self, tmp_path):
        target1 = tmp_path / "settings1.json"
        target2 = tmp_path / "settings2.json"

        PiHooksInstaller.create(target1).install()
        PiHooksInstaller.create(target2).install()

        data1 = json.loads(target1.read_text(encoding="utf-8"))
        data2 = json.loads(target2.read_text(encoding="utf-8"))

        assert (
            json.dumps(data1, sort_keys=True)
            == json.dumps(data2, sort_keys=True)
        ), "Multiple runs should produce identical settings"
