"""Tests for install_pi_config.main."""

import json
from pathlib import Path

import pytest

from ai_toolkit.install_pi_config import main as main_module
from ai_toolkit.install_pi_config.main import (
    _merge_json,
    _register_opencode_provider,
    _register_pi_provider,
    _sync_auth,
    main,
)


class TestMergeJson:
    @pytest.mark.integration
    def test_when_file_does_not_exist_then_creates_file_with_entry(
        self, tmp_path: Path
    ) -> None:
        p = tmp_path / "sub" / "data.json"
        _merge_json(p, "providers", "Cline", {"name": "Cline"})
        assert p.is_file()
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data == {"providers": {"Cline": {"name": "Cline"}}}

    @pytest.mark.integration
    def test_when_file_exists_then_merges_under_key_entry(self, tmp_path: Path) -> None:
        p = tmp_path / "data.json"
        p.write_text(json.dumps({"existing": {"a": 1}}), encoding="utf-8")
        _merge_json(p, "providers", "Cline", {"name": "Cline"})
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data == {
            "existing": {"a": 1},
            "providers": {"Cline": {"name": "Cline"}},
        }

    @pytest.mark.integration
    def test_when_file_has_invalid_json_then_starts_fresh(self, tmp_path: Path) -> None:
        p = tmp_path / "data.json"
        p.write_text("not json", encoding="utf-8")
        _merge_json(p, "providers", "Cline", {"name": "Cline"})
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data == {"providers": {"Cline": {"name": "Cline"}}}

    @pytest.mark.integration
    def test_when_entry_key_already_exists_then_overwrites(
        self, tmp_path: Path
    ) -> None:
        p = tmp_path / "data.json"
        p.write_text(
            json.dumps({"providers": {"Cline": {"old": True}}}), encoding="utf-8"
        )
        _merge_json(p, "providers", "Cline", {"name": "Cline"})
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data == {"providers": {"Cline": {"name": "Cline"}}}

    @pytest.mark.integration
    def test_when_key_does_not_exist_in_data_then_creates_it(
        self, tmp_path: Path
    ) -> None:
        p = tmp_path / "data.json"
        p.write_text(json.dumps({}), encoding="utf-8")
        _merge_json(p, "providers", "Cline", {"name": "Cline"})
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data == {"providers": {"Cline": {"name": "Cline"}}}

    @pytest.mark.integration
    def test_when_successful_then_returns_true(self, tmp_path: Path) -> None:
        p = tmp_path / "data.json"
        result = _merge_json(p, "x", "y", {"z": 1})
        assert result is True

    @pytest.mark.integration
    def test_output_has_newline_terminated_json(self, tmp_path: Path) -> None:
        p = tmp_path / "data.json"
        _merge_json(p, "k", "e", {"v": 1})
        content = p.read_text(encoding="utf-8")
        assert content.endswith("\n")


class TestSyncAuth:
    @pytest.mark.integration
    def test_when_file_does_not_exist_then_creates_file(self, tmp_path: Path) -> None:
        p = tmp_path / "auth.json"
        _sync_auth(p, "sk-ant-abc123")
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data == {"cline": {"type": "api_key", "key": "sk-ant-abc123"}}

    @pytest.mark.integration
    def test_when_file_exists_then_merges_cline_key(self, tmp_path: Path) -> None:
        p = tmp_path / "auth.json"
        p.write_text(json.dumps({"other": {"key": "val"}}), encoding="utf-8")
        _sync_auth(p, "sk-ant-abc123")
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data == {
            "other": {"key": "val"},
            "cline": {"type": "api_key", "key": "sk-ant-abc123"},
        }

    @pytest.mark.integration
    def test_when_invalid_json_then_starts_fresh(self, tmp_path: Path) -> None:
        p = tmp_path / "auth.json"
        p.write_text("{bad", encoding="utf-8")
        _sync_auth(p, "sk-ant-abc123")
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data == {"cline": {"type": "api_key", "key": "sk-ant-abc123"}}

    @pytest.mark.integration
    def test_when_successful_then_returns_true(self, tmp_path: Path) -> None:
        result = _sync_auth(tmp_path / "auth.json", "sk-ant-abc123")
        assert result is True


class TestRegisterPiProvider:
    @pytest.mark.integration
    def test_when_no_base_url_then_uses_default_anthropic_url(
        self, tmp_path: Path
    ) -> None:
        p = tmp_path / "models.json"
        _register_pi_provider(p, "")
        data = json.loads(p.read_text(encoding="utf-8"))
        provider = data["providers"]["Cline"]
        assert provider["baseUrl"] == "https://api.anthropic.com"
        assert provider["api"] == "anthropic-messages"
        assert len(provider["models"]) == 3

    @pytest.mark.integration
    def test_when_base_url_provided_then_overrides_default(
        self, tmp_path: Path
    ) -> None:
        p = tmp_path / "models.json"
        _register_pi_provider(p, "https://custom.example.com")
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data["providers"]["Cline"]["baseUrl"] == "https://custom.example.com"

    @pytest.mark.integration
    def test_models_include_all_three_claude_models(self, tmp_path: Path) -> None:
        p = tmp_path / "models.json"
        _register_pi_provider(p, "")
        model_ids = {
            m["id"]
            for m in json.loads(p.read_text(encoding="utf-8"))["providers"]["Cline"][
                "models"
            ]
        }
        assert model_ids == {
            "claude-sonnet-4-20250514",
            "claude-opus-4-20250514",
            "claude-haiku-3-5-20241022",
        }


class TestRegisterOpencodeProvider:
    @pytest.mark.integration
    def test_when_no_base_url_then_uses_default_v1_url(self, tmp_path: Path) -> None:
        p = tmp_path / "opencode.json"
        _register_opencode_provider(p, "")
        data = json.loads(p.read_text(encoding="utf-8"))
        provider = data["provider"]["Cline"]
        assert provider["options"]["baseURL"] == "https://api.anthropic.com/v1"
        assert provider["options"]["apiKey"] == "{env:CLINE_API_KEY}"

    @pytest.mark.integration
    def test_when_base_url_provided_then_uses_custom_url(self, tmp_path: Path) -> None:
        p = tmp_path / "opencode.json"
        _register_opencode_provider(p, "https://custom.example.com")
        data = json.loads(p.read_text(encoding="utf-8"))
        assert (
            data["provider"]["Cline"]["options"]["baseURL"]
            == "https://custom.example.com"
        )

    @pytest.mark.integration
    def test_models_are_included_in_entry(self, tmp_path: Path) -> None:
        p = tmp_path / "opencode.json"
        _register_opencode_provider(p, "")
        models = json.loads(p.read_text(encoding="utf-8"))["provider"]["Cline"][
            "models"
        ]
        assert "claude-sonnet-4-20250514" in models
        assert "claude-opus-4-20250514" in models
        assert "claude-haiku-3-5-20241022" in models


class TestMain:
    @pytest.mark.integration
    def test_when_dotenv_missing_then_registers_without_auth(self, tmp_path: Path) -> None:
        rc = main(dotenv_path=tmp_path / ".env")
        assert rc == 0

    @pytest.mark.integration
    def test_when_dotenv_has_no_cline_key_then_registers_without_auth(
        self, tmp_path: Path
    ) -> None:
        dotenv = tmp_path / ".env"
        dotenv.write_text("OTHER_KEY=val\n", encoding="utf-8")
        rc = main(dotenv_path=dotenv)
        assert rc == 0

    @pytest.mark.integration
    def test_when_key_present_then_syncs_auth_and_providers_and_returns_zero(
        self, tmp_path: Path
    ) -> None:
        dotenv = tmp_path / ".env"
        dotenv.write_text("CLINE_API_KEY=sk-ant-abc123\n", encoding="utf-8")
        auth = tmp_path / "auth.json"
        models = tmp_path / "models.json"
        opencode_cfg = tmp_path / "opencode.json"

        rc = main(
            dotenv_path=dotenv,
            auth_path=auth,
            pi_models_path=models,
            opencode_config_path=opencode_cfg,
        )

        assert rc == 0
        assert json.loads(auth.read_text(encoding="utf-8")) == {
            "cline": {"type": "api_key", "key": "sk-ant-abc123"},
        }
        pi_data = json.loads(models.read_text(encoding="utf-8"))
        assert pi_data["providers"]["Cline"]["baseUrl"] == "https://api.anthropic.com"
        oc_data = json.loads(opencode_cfg.read_text(encoding="utf-8"))
        assert (
            oc_data["provider"]["Cline"]["options"]["baseURL"]
            == "https://api.anthropic.com/v1"
        )

    @pytest.mark.integration
    def test_when_base_url_in_dotenv_then_passes_to_providers(
        self, tmp_path: Path
    ) -> None:
        dotenv = tmp_path / ".env"
        dotenv.write_text(
            "CLINE_API_KEY=sk-ant-abc123\nCLINE_API_BASE_URL=https://custom.example.com\n",
            encoding="utf-8",
        )
        auth = tmp_path / "auth.json"
        models = tmp_path / "models.json"
        opencode_cfg = tmp_path / "opencode.json"

        rc = main(
            dotenv_path=dotenv,
            auth_path=auth,
            pi_models_path=models,
            opencode_config_path=opencode_cfg,
        )

        assert rc == 0
        pi_data = json.loads(models.read_text(encoding="utf-8"))
        assert pi_data["providers"]["Cline"]["baseUrl"] == "https://custom.example.com"
        oc_data = json.loads(opencode_cfg.read_text(encoding="utf-8"))
        assert (
            oc_data["provider"]["Cline"]["options"]["baseURL"]
            == "https://custom.example.com"
        )

    @pytest.mark.integration
    def test_with_default_paths_when_home_constants_monkeypatched(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        dotenv = tmp_path / ".env"
        dotenv.write_text("CLINE_API_KEY=sk-ant-abc123\n", encoding="utf-8")

        pi_dir = tmp_path / ".pi" / "agent"
        opencode_dir = tmp_path / ".config" / "opencode"
        monkeypatch.setattr(main_module, "PI_AUTH_PATH", pi_dir / "auth.json")
        monkeypatch.setattr(main_module, "PI_MODELS_PATH", pi_dir / "models.json")
        monkeypatch.setattr(
            main_module, "OPENCODE_CONFIG_PATH", opencode_dir / "opencode.json"
        )

        rc = main(dotenv_path=dotenv)

        assert rc == 0
        assert (pi_dir / "auth.json").is_file()
        assert (pi_dir / "models.json").is_file()
        assert (opencode_dir / "opencode.json").is_file()

    @pytest.mark.unit
    def test_when_sync_auth_fails_then_returns_one(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        dotenv = tmp_path / ".env"
        dotenv.write_text("CLINE_API_KEY=sk-ant-abc123\n", encoding="utf-8")
        monkeypatch.setattr(main_module, "_sync_auth", lambda _a, _k: False)

        rc = main(dotenv_path=dotenv, auth_path=tmp_path / "auth.json")
        assert rc == 1

    @pytest.mark.unit
    def test_when_register_pi_provider_fails_then_returns_one(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        dotenv = tmp_path / ".env"
        dotenv.write_text("CLINE_API_KEY=sk-ant-abc123\n", encoding="utf-8")
        monkeypatch.setattr(main_module, "_register_pi_provider", lambda _p, _b: False)

        rc = main(dotenv_path=dotenv, pi_models_path=tmp_path / "models.json")
        assert rc == 1

    @pytest.mark.unit
    def test_when_register_opencode_provider_fails_then_returns_one(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        dotenv = tmp_path / ".env"
        dotenv.write_text("CLINE_API_KEY=sk-ant-abc123\n", encoding="utf-8")
        monkeypatch.setattr(
            main_module, "_register_opencode_provider", lambda _c, _b: False
        )

        rc = main(dotenv_path=dotenv, opencode_config_path=tmp_path / "opencode.json")
        assert rc == 1

    @pytest.mark.unit
    def test_when_all_syncs_fail_then_accumulates_errors_and_returns_one(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        dotenv = tmp_path / ".env"
        dotenv.write_text("CLINE_API_KEY=sk-ant-abc123\n", encoding="utf-8")
        monkeypatch.setattr(main_module, "_sync_auth", lambda _a, _k: False)
        monkeypatch.setattr(main_module, "_register_pi_provider", lambda _p, _b: False)
        monkeypatch.setattr(
            main_module, "_register_opencode_provider", lambda _c, _b: False
        )

        rc = main(dotenv_path=dotenv)
        assert rc == 1
