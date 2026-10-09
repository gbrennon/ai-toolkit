from collections.abc import Iterable, Mapping, Sequence
import math
from pathlib import Path
import re
from typing import cast

from .errors import PathEscapeError, SchemaValidationError
from .models import HookDefinition, HookReference, SkillDefinition, SkillReference
from .path_containment import PathContainment
from .paths import RegistryPaths
from .storage import JsonDocumentStore

_SCHEMA_VERSION = 1
_ID = re.compile(r"[a-z0-9][a-z0-9._-]*")
_SKILL_FIELDS = frozenset({"id", "version", "triggers"})
_HOOK_REFERENCE_FIELDS = frozenset({"id", "version"})
_HOOK_FIELDS = frozenset({"id", "version", "events", "enabled", "argv", "timeout", "failurePolicy", "audit"})


def parse_skill_manifest(value: object) -> tuple[SkillReference, ...]:
    """Parse a strict skills manifest without reading repository files."""
    entries = _entries(_manifest_mapping(value, "skills"), "skills")
    references: list[SkillReference] = []
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        item = _entry_mapping(entry, index, "skills")
        _unknown(item, _SKILL_FIELDS, f"skills.entries[{index}]")
        skill_id = _required_text(item, "id", f"skills.entries[{index}]")
        version = _required_text(item, "version", f"skills.entries[{index}]")
        _validate_id(skill_id, f"skills.entries[{index}].id")
        _check_duplicate(skill_id, seen, "skill")
        references.append(SkillReference(skill_id, version, _triggers(item.get("triggers"), f"skills.entries[{index}].triggers")))
    return tuple(references)


def load_skills(references: Iterable[SkillReference], paths: RegistryPaths) -> tuple[SkillDefinition, ...]:
    """Resolve each skill exactly once below the global skills directory."""
    definitions: list[SkillDefinition] = []
    seen: set[Path] = set()
    containment = PathContainment(paths.skills_dir)
    for reference in references:
        _validate_id(reference.id, "skill id")
        try:
            skill_path = containment.resolve(f"{reference.id}.md")
        except PathEscapeError as error:
            raise SchemaValidationError(f"unsafe skill path: {reference.id}") from error
        if skill_path in seen:
            raise SchemaValidationError(f"duplicate skill path: {skill_path}")
        if not skill_path.is_file():
            raise SchemaValidationError(f"missing global skill: {skill_path}")
        seen.add(skill_path)
        definitions.append(SkillDefinition(reference.id, reference.version, skill_path, reference.triggers))
    return tuple(definitions)


def select_skills(definitions: Iterable[SkillDefinition], triggers: Iterable[str]) -> tuple[SkillDefinition, ...]:
    """Select only exact trigger matches and explicitly declared always skills."""
    selected = frozenset(triggers)
    return tuple(item for item in definitions if "always" in item.triggers or selected.intersection(item.triggers))


def parse_hook_manifest(value: object) -> tuple[HookReference, ...]:
    """Parse the strict per-repository hooks manifest."""
    entries = _entries(_manifest_mapping(value, "hooks"), "hooks")
    references: list[HookReference] = []
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        item = _entry_mapping(entry, index, "hooks")
        _unknown(item, _HOOK_REFERENCE_FIELDS, f"hooks.entries[{index}]")
        hook_id = _required_text(item, "id", f"hooks.entries[{index}]")
        version = _required_text(item, "version", f"hooks.entries[{index}]")
        _validate_id(hook_id, f"hooks.entries[{index}].id")
        _check_duplicate(hook_id, seen, "hook")
        references.append(HookReference(hook_id, version))
    return tuple(references)


def load_hooks(references: Iterable[HookReference], paths: RegistryPaths) -> tuple[HookDefinition, ...]:
    """Resolve and validate each referenced global hook definition."""
    definitions: list[HookDefinition] = []
    seen: set[Path] = set()
    containment = PathContainment(paths.hooks_dir)
    for reference in references:
        _validate_id(reference.id, "hook id")
        try:
            hook_dir = containment.resolve(reference.id)
        except PathEscapeError as error:
            raise SchemaValidationError(f"unsafe hook path: {reference.id}") from error
        if hook_dir in seen:
            raise SchemaValidationError(f"duplicate hook path: {hook_dir}")
        manifest_path = hook_dir / "hook.json"
        if not manifest_path.is_file():
            raise SchemaValidationError(f"missing global hook manifest: {manifest_path}")
        definition = _hook_definition(JsonDocumentStore().read(manifest_path), hook_dir, reference)
        seen.add(hook_dir)
        definitions.append(definition)
    return tuple(definitions)


def select_hooks(definitions: Iterable[HookDefinition], event: str) -> tuple[HookDefinition, ...]:
    """Select enabled hooks whose event names exactly match the requested event."""
    return tuple(item for item in definitions if item.enabled and event in item.events)


def _manifest_mapping(value: object, kind: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(f"{kind}.json must be an object")
    _unknown(value, frozenset({"schemaVersion", "entries"}), kind)
    if value.get("schemaVersion") != _SCHEMA_VERSION or isinstance(value.get("schemaVersion"), bool):
        raise SchemaValidationError(f"{kind}.json schemaVersion must be 1")
    return cast(Mapping[str, object], value)


def _entries(mapping: Mapping[str, object], kind: str) -> Sequence[object]:
    entries = mapping.get("entries")
    if not _is_string_safe_sequence(entries):
        raise SchemaValidationError(f"{kind}.json entries must be an array")
    return cast(Sequence[object], entries)


def _entry_mapping(value: object, index: int, kind: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(f"{kind}.entries[{index}] must be an object")
    return cast(Mapping[str, object], value)


def _unknown(value: Mapping[str, object], allowed: frozenset[str], prefix: str) -> None:
    unknown = [key for key in value if key not in allowed]
    if unknown:
        raise SchemaValidationError(f"{prefix} contains unknown field {unknown[0]}")


def _required_text(value: Mapping[str, object], field: str, prefix: str) -> str:
    item = value.get(field)
    if not isinstance(item, str) or not item.strip():
        raise SchemaValidationError(f"{prefix}.{field} must be nonempty text")
    return item


def _validate_id(value: str, field: str) -> None:
    if _ID.fullmatch(value) is None:
        raise SchemaValidationError(f"{field} must be a safe registry identifier")


def _check_duplicate(value: str, seen: set[str], kind: str) -> None:
    if value in seen:
        raise SchemaValidationError(f"duplicate {kind} id: {value}")
    seen.add(value)


def _triggers(value: object, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    values = _string_values(value, field)
    if len(set(values)) != len(values):
        raise SchemaValidationError(f"{field} contains duplicate trigger")
    return values


def _hook_definition(value: object, hook_dir: Path, reference: HookReference) -> HookDefinition:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(f"hook.json for {reference.id} must be an object")
    item = cast(Mapping[str, object], value)
    _unknown(item, _HOOK_FIELDS, f"hooks/{reference.id}/hook.json")
    hook_id = _required_text(item, "id", "hook.json")
    version = _required_text(item, "version", "hook.json")
    if hook_id != reference.id or version != reference.version:
        raise SchemaValidationError(f"hook.json identity does not match hooks.json for {reference.id}")
    events = _string_values(item.get("events"), "hook.json.events")
    enabled = _boolean(item.get("enabled"), "hook.json.enabled")
    argv = _string_values(item.get("argv"), "hook.json.argv")
    _validate_argv(argv, hook_dir)
    timeout = _timeout(item.get("timeout"))
    policy = _failure_policy(item.get("failurePolicy"))
    audit = _boolean(item.get("audit"), "hook.json.audit")
    return HookDefinition(hook_id, version, events, enabled, argv, timeout, policy, audit, hook_dir)


def _string_values(value: object, field: str) -> tuple[str, ...]:
    if not _is_string_safe_sequence(value):
        raise SchemaValidationError(f"{field} must be a nonempty array of strings")
    values = cast(Sequence[object], value)
    if not _all_nonempty_strings(values):
        raise SchemaValidationError(f"{field} must contain nonempty strings")
    return tuple(cast(str, item) for item in values)


def _all_nonempty_strings(values: Sequence[object]) -> bool:
    if not values:
        return False
    return all(isinstance(item, str) and bool(item) for item in values)


def _is_string_safe_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _boolean(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise SchemaValidationError(f"{field} must be boolean")
    return value


def _timeout(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise SchemaValidationError("hook.json.timeout must be a positive finite number")
    return float(value)


def _failure_policy(value: object) -> str:
    if value not in {"block", "warn", "ignore"}:
        raise SchemaValidationError("hook.json.failurePolicy must be block, warn, or ignore")
    return cast(str, value)


def _validate_argv(argv: Sequence[str], hook_dir: Path) -> None:
    for component in argv:
        _validate_argv_component(component, hook_dir)


def _validate_argv_component(component: str, hook_dir: Path) -> None:
    candidate = Path(component)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise SchemaValidationError(f"hook executable path escapes hook directory: {component}")
    if len(candidate.parts) > 1 and not (hook_dir / candidate).resolve().is_relative_to(hook_dir.resolve()):
        raise SchemaValidationError(f"hook executable path escapes hook directory: {component}")
