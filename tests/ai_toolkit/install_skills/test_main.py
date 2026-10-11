from pathlib import Path
from unittest.mock import patch

import pytest

from ai_toolkit.install_skills.main import main


class TestMain:
    @pytest.mark.unit
    def test_main_when_skills_yaml_missing_then_returns_one(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        result = main()
        assert result == 1

    @pytest.mark.unit
    def test_main_when_npx_not_available_then_returns_one(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "skills.yaml").write_text("skills: []\n")
        with patch(
            "ai_toolkit.install_skills.main.shell_command_exists",
            return_value=False,
        ):
            result = main()
            assert result == 1

    @pytest.mark.unit
    def test_main_when_update_fails_then_returns_one(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "skills.yaml").write_text("skills: []\n")
        with (
            patch(
                "ai_toolkit.install_skills.main.shell_command_exists",
                return_value=True,
            ),
            patch(
                "ai_toolkit.install_skills.main.update_skills",
                return_value=False,
            ),
        ):
            result = main()
            assert result == 1

    @pytest.mark.unit
    def test_main_when_all_succeed_then_returns_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "skills.yaml").write_text("skills: []\n")
        with (
            patch(
                "ai_toolkit.install_skills.main.shell_command_exists",
                return_value=True,
            ),
            patch(
                "ai_toolkit.install_skills.main.update_skills",
                return_value=True,
            ),
            patch(
                "ai_toolkit.install_skills.main.NpxSkillInstaller",
            ) as mock_npx,
            patch(
                "ai_toolkit.install_skills.main.LocalSkillInstaller",
            ),
            patch(
                "ai_toolkit.install_skills.main.Path.home",
                return_value=tmp_path,
            ),
        ):
            mock_npx_instance = mock_npx.return_value
            mock_npx_instance.install.return_value = True
            result = main()
            assert result == 0

    @pytest.mark.unit
    def test_main_when_remote_skills_fail_then_returns_one(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "skills.yaml").write_text("skills: []\n")
        with (
            patch(
                "ai_toolkit.install_skills.main.shell_command_exists",
                return_value=True,
            ),
            patch(
                "ai_toolkit.install_skills.main.update_skills",
                return_value=True,
            ),
            patch(
                "ai_toolkit.install_skills.main.install_remote_skills",
                return_value=["failed-skill"],
            ),
            patch(
                "ai_toolkit.install_skills.main.Path.home",
                return_value=tmp_path,
            ),
        ):
            result = main()
            assert result == 1

    @pytest.mark.unit
    def test_main_when_local_skills_fail_then_returns_one(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "skills.yaml").write_text("skills: []\n")
        (tmp_path / "skills").mkdir()
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        with (
            patch(
                "ai_toolkit.install_skills.main.shell_command_exists",
                return_value=True,
            ),
            patch(
                "ai_toolkit.install_skills.main.update_skills",
                return_value=True,
            ),
            patch(
                "ai_toolkit.install_skills.main.install_remote_skills",
                return_value=[],
            ),
            patch(
                "ai_toolkit.install_skills.main.install_local_skills",
                return_value=["local-failed"],
            ),
            patch(
                "ai_toolkit.install_skills.main.LocalSkillInstaller",
            ),
            patch(
                "ai_toolkit.install_skills.main.Path.home",
                return_value=agents_dir,
            ),
        ):
            result = main()
            assert result == 1

    @pytest.mark.unit
    def test_main_when_local_dir_missing_then_skips_local(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "skills.yaml").write_text("skills: []\n")
        with (
            patch(
                "ai_toolkit.install_skills.main.shell_command_exists",
                return_value=True,
            ),
            patch(
                "ai_toolkit.install_skills.main.update_skills",
                return_value=True,
            ),
            patch(
                "ai_toolkit.install_skills.main.install_remote_skills",
                return_value=[],
            ),
            patch(
                "ai_toolkit.install_skills.main.Path.home",
                return_value=tmp_path,
            ),
        ):
            result = main()
            assert result == 0
