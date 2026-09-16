"""Tests for install_provider_blocks.main."""

import json
from pathlib import Path

import pytest

from ai_toolkit.install_provider_blocks import main as main_module
from ai_toolkit.install_provider_blocks.main import (
    _block_cline_providers,
    _block_omp_providers,
    _read_json,
    _read_yaml,
    _write_json,
    _write_yaml,
    install,
)


class TestReadYaml:
    @pytest.mark.unit
    def test_when_file_does_not_exist_then_returns_empty_dict(
        self, tmp_path: Path
    ) -> None:
        assert _read_yaml(tmp_path / "nonexistent.yml") == {}

    @pytest.mark.integration
    def test_when_file_exists_then_parses_yaml(self, tmp_path: Path) -> None:
        p = tmp_path / "data.yml"
        p.write_text("key: value\nlist:\n  - a\n  - b\n", encoding="utf-8")
        assert _read_yaml(p) == {"key": "value", "list": ["a", "b"]}

    @pytest.mark.integration
    def test_when_file_is_empty_then_returns_empty_dict(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.yml"
        p.write_text("", encoding="utf-8")
        assert _read_yaml(p) == {}

    @pytest.mark.integration
    def test_when_invalid_yaml_then_returns_empty_dict(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.yml"
        p.write_text(": invalid yaml :::", encoding="utf-8")
        assert _read_yaml(p) == {}


class TestWriteYaml:
    @pytest.mark.integration
    def test_writes_yaml_and_creates_dirs(self, tmp_path: Path) -> None:
        p = tmp_path / "sub" / "data.yml"
        assert _write_yaml(p, {"key": "value"}) is True
        assert p.is_file()
        assert _read_yaml(p) == {"key": "value"}

    @pytest.mark.integration
    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        p = tmp_path / "data.yml"
        p.write_text("old: true\n", encoding="utf-8")
        _write_yaml(p, {"new": True})
        assert _read_yaml(p) == {"new": True}


class TestReadJson:
    @pytest.mark.unit
    def test_when_file_does_not_exist_then_returns_empty_dict(
        self, tmp_path: Path
    ) -> None:
        assert _read_json(tmp_path / "nope.json") == {}

    @pytest.mark.integration
    def test_when_file_exists_then_parses_json(self, tmp_path: Path) -> None:
        p = tmp_path / "data.json"
        p.write_text('{"key": "value"}', encoding="utf-8")
        assert _read_json(p) == {"key": "value"}

    @pytest.mark.integration
    def test_when_invalid_json_then_returns_empty_dict(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.json"
        p.write_text("not json", encoding="utf-8")
        assert _read_json(p) == {}


class TestWriteJson:
    @pytest.mark.integration
    def test_writes_json_and_creates_dirs(self, tmp_path: Path) -> None:
        p = tmp_path / "sub" / "data.json"
        assert _write_json(p, {"x": 1}) is True
        assert p.is_file()
        assert _read_json(p) == {"x": 1}

    @pytest.mark.integration
    def test_output_has_trailing_newline(self, tmp_path: Path) -> None:
        p = tmp_path / "data.json"
        _write_json(p, {"a": 1})
        assert p.read_text(encoding="utf-8").endswith("\n")


class TestBlockOmpProviders:
    @pytest.mark.integration
    def test_when_both_disabled_then_adds_them(self, tmp_path: Path) -> None:
        p = tmp_path / "models.yml"
        p.write_text("disabledProviders:\n  - other\n", encoding="utf-8")
        assert _block_omp_providers(p) is True
        data = _read_yaml(p)
        assert data["disabledProviders"] == ["other"]

    @pytest.mark.integration
    def test_when_already_blocked_then_no_change(self, tmp_path: Path) -> None:
        p = tmp_path / "models.yml"
        p.write_text(
            "disabledProviders:\n  - openai\n  - anthropic\n", encoding="utf-8"
        )
        assert _block_omp_providers(p) is True
        data = _read_yaml(p)
        assert data["disabledProviders"] == []

    @pytest.mark.integration
    def test_when_partially_blocked_then_adds_missing(self, tmp_path: Path) -> None:
        p = tmp_path / "models.yml"
        p.write_text("disabledProviders:\n  - openai\n", encoding="utf-8")
        assert _block_omp_providers(p) is True
        data = _read_yaml(p)
        assert data["disabledProviders"] == []

    @pytest.mark.integration
    def test_when_file_does_not_exist_then_creates_it(self, tmp_path: Path) -> None:
        p = tmp_path / "new" / "models.yml"
        assert _block_omp_providers(p) is True
        data = _read_yaml(p)
        assert data == {}

    @pytest.mark.integration
    def test_preserves_existing_providers(self, tmp_path: Path) -> None:
        p = tmp_path / "models.yml"
        p.write_text(
            "providers:\n  cline:\n    baseUrl: https://api.cline.bot/v1\n",
            encoding="utf-8",
        )
        assert _block_omp_providers(p) is True
        data = _read_yaml(p)
        assert data["providers"]["cline"]["baseUrl"] == "https://api.cline.bot/v1"
        assert "disabledProviders" not in data


class TestBlockClineProviders:
    @pytest.mark.integration
    def test_when_both_present_then_removes_them(self, tmp_path: Path) -> None:
        p = tmp_path / "providers.json"
        p.write_text(
            json.dumps(
                {
                    "version": 1,
                    "providers": {
                        "openai": {"settings": {"model": "gpt-4"}},
                        "anthropic": {"settings": {"model": "claude"}},
                        "cline": {"settings": {"model": "deepseek"}},
                    },
                }
            ),
            encoding="utf-8",
        )
        assert _block_cline_providers(p) is True
        data = _read_json(p)
        assert data["providers"]["openai"] == {"settings": {"model": "gpt-4"}}
        assert data["providers"]["anthropic"] == {"settings": {"model": "claude"}}
        assert "cline" in data["providers"]

    @pytest.mark.integration
    def test_when_none_present_then_no_change(self, tmp_path: Path) -> None:
        p = tmp_path / "providers.json"
        p.write_text(
            json.dumps(
                {
                    "providers": {"cline": {"settings": {"model": "ds"}}},
                }
            ),
            encoding="utf-8",
        )
        assert _block_cline_providers(p) is True
        data = _read_json(p)
        assert data["providers"] == {"cline": {"settings": {"model": "ds"}}}

    @pytest.mark.integration
    def test_when_partially_present_then_removes_present(self, tmp_path: Path) -> None:
        p = tmp_path / "providers.json"
        p.write_text(
            json.dumps(
                {
                    "providers": {"openai": {"settings": {"model": "gpt"}}},
                }
            ),
            encoding="utf-8",
        )
        assert _block_cline_providers(p) is True
        assert "openai" in _read_json(p)["providers"]

    @pytest.mark.integration
    def test_when_file_does_not_exist_then_noop(self, tmp_path: Path) -> None:
        assert _block_cline_providers(tmp_path / "nope.json") is True

    @pytest.mark.integration
    def test_when_empty_json_then_noop(self, tmp_path: Path) -> None:
        p = tmp_path / "providers.json"
        p.write_text("{}", encoding="utf-8")
        assert _block_cline_providers(p) is True


class TestInstall:
    @pytest.mark.integration
    def test_blocks_both_providers_on_both_agents(self, tmp_path: Path) -> None:
        omp = tmp_path / "models.yml"
        omp.write_text("disabledProviders:\n  - other\n", encoding="utf-8")
        cline = tmp_path / "providers.json"
        cline.write_text(
            json.dumps(
                {
                    "providers": {
                        "openai": {"settings": {"model": "gpt"}},
                        "anthropic": {"settings": {"model": "claude"}},
                    },
                }
            ),
            encoding="utf-8",
        )

        rc = install(omp_models_path=omp, cline_providers_path=cline)
        assert rc == 0

        omp_data = _read_yaml(omp)
        assert omp_data["disabledProviders"] == ["other"]

        cline_data = _read_json(cline)
        assert "openai" in cline_data["providers"]
        assert "anthropic" in cline_data["providers"]

    @pytest.mark.integration
    def test_when_already_blocked_then_idempotent(self, tmp_path: Path) -> None:
        omp = tmp_path / "models.yml"
        omp.write_text(
            "disabledProviders:\n  - openai\n  - anthropic\n",
            encoding="utf-8",
        )
        cline = tmp_path / "providers.json"
        cline.write_text(
            json.dumps(
                {
                    "providers": {"cline": {"settings": {"model": "ds"}}},
                }
            ),
            encoding="utf-8",
        )

        rc = install(omp_models_path=omp, cline_providers_path=cline)
        assert rc == 0

    @pytest.mark.unit
    def test_when_omp_block_fails_then_returns_one(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(main_module, "_allow_omp_providers", lambda _p: False)
        rc = install(
            omp_models_path=tmp_path / "m.yml",
            cline_providers_path=tmp_path / "p.json",
        )
        assert rc == 1

    @pytest.mark.unit
    def test_when_cline_block_fails_then_returns_one(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(main_module, "_allow_cline_providers", lambda _p: False)
        rc = install(
            omp_models_path=tmp_path / "m.yml",
            cline_providers_path=tmp_path / "p.json",
        )
        assert rc == 1
