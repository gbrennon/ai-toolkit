from pathlib import Path

import pytest

from ai_toolkit.agent_registry.dependencies import (
    load_hooks,
    parse_hook_manifest,
    select_hooks,
)
from ai_toolkit.agent_registry.errors import SchemaValidationError
from ai_toolkit.agent_registry.models import HookDefinition
from ai_toolkit.agent_registry.paths import RegistryPaths


def _write_hook(paths: RegistryPaths, hook_id: str, payload: dict[str, object]) -> None:
    directory = paths.hooks_dir / hook_id
    directory.mkdir(parents=True, exist_ok=True)
    import json

    (directory / "hook.json").write_text(json.dumps(payload), encoding="utf-8")


def _hook_payload(hook_id: str = "check", enabled: bool = True) -> dict[str, object]:
    return {
        "id": hook_id,
        "version": "1",
        "events": ["register"],
        "enabled": enabled,
        "argv": ["run-hook", "--safe"],
        "timeout": 2.5,
        "failurePolicy": "warn",
        "audit": True,
    }


def test_hooks_validate_global_definition_and_disabled_selection(tmp_path: Path) -> None:
    paths = RegistryPaths(tmp_path / "registry")
    _write_hook(paths, "check", _hook_payload())
    _write_hook(paths, "disabled", _hook_payload("disabled", False))
    manifest = {
        "schemaVersion": 1,
        "entries": [
            {"id": "check", "version": "1"},
            {"id": "disabled", "version": "1"},
        ],
    }

    definitions = load_hooks(parse_hook_manifest(manifest), paths)

    assert definitions[0] == HookDefinition(
        id="check",
        version="1",
        events=("register",),
        enabled=True,
        argv=("run-hook", "--safe"),
        timeout=2.5,
        failure_policy="warn",
        audit=True,
        directory=paths.hooks_dir / "check",
    )
    assert [hook.id for hook in select_hooks(definitions, "register")] == ["check"]


def test_hooks_reject_unknown_fields_invalid_timeout_and_policy(tmp_path: Path) -> None:
    paths = RegistryPaths(tmp_path / "registry")
    for update in (
        {"extra": True},
        {"timeout": 0},
        {"timeout": float("inf")},
        {"failurePolicy": "retry"},
        {"argv": ["../outside/hook"]},
    ):
        payload = _hook_payload()
        payload.update(update)
        _write_hook(paths, "check", payload)
        with pytest.raises(SchemaValidationError):
            load_hooks(parse_hook_manifest({"schemaVersion": 1, "entries": [{"id": "check", "version": "1"}]}), paths)


def test_hooks_reject_duplicate_and_unsafe_manifest_entries() -> None:
    manifests = [
        {"schemaVersion": 1, "entries": [{"id": "x", "version": "1", "extra": 1}]},
        {
            "schemaVersion": 1,
            "entries": [{"id": "x", "version": "1"}, {"id": "x", "version": "1"}],
        },
        {"schemaVersion": 1, "entries": [{"id": "../x", "version": "1"}]},
        {"schemaVersion": 1, "entries": [{"id": "/tmp/x", "version": "1"}]},
    ]

    for manifest in manifests:
        with pytest.raises(SchemaValidationError):
            parse_hook_manifest(manifest)
