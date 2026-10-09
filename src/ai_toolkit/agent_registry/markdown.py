from collections.abc import Iterable
import re

from .errors import SchemaValidationError
from .models import AgentConfigFrontMatter, HookReference, RegistryDocument, RepositoryRecord, SkillReference, ValidationIssue, ValidationReport
from .validation import parse_utc_timestamp

_REQUIRED_HEADINGS = (
    "Scope", "Precedence", "Repository identity", "Required behavior",
    "Architecture and coding standards", "Verification", "Skills", "Hooks",
    "Security and secrets", "Change policy",
)
_FRONT_MATTER_FIELDS = ("registrySchema", "repositoryId", "gitRemote", "configVersion", "lastReviewed")
_HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$")


def render_agent_markdown(record: RepositoryRecord, registry: RegistryDocument, skills: Iterable[SkillReference] = (), hooks: Iterable[HookReference] = ()) -> str:
    """Render a deterministic global AGENT.md document."""
    front_matter = AgentConfigFrontMatter(registry.schema_version, record.repository_id, record.git_remote, 1, registry.updated_at)
    lines = ["---", *(f"{key}: {value}" for key, value in front_matter.to_json().items()), "---"]
    return "\n".join(lines + _render_body(record, skills, hooks)) + "\n"


def render_agent_document(record: RepositoryRecord, registry: RegistryDocument, skills: Iterable[SkillReference] = (), hooks: Iterable[HookReference] = ()) -> str:
    """Compatibility name for the deterministic renderer."""
    return render_agent_markdown(record, registry, skills, hooks)


def parse_agent_document(content: str) -> tuple[AgentConfigFrontMatter, tuple[str, ...]]:
    """Parse strict front matter and required heading names."""
    front_matter, body = _split_front_matter(content)
    return _parse_front_matter(front_matter), _parse_headings(body)


def parse_front_matter(content: str) -> AgentConfigFrontMatter:
    """Parse only the strict front matter block from an AGENT document."""
    front_matter, _ = _split_front_matter(content)
    return _parse_front_matter(front_matter)


def validate_agent_markdown(content: str, record: RepositoryRecord, registry_schema: int = 1) -> ValidationReport:
    """Validate AGENT front matter and headings against one registry record."""
    try:
        front_matter, headings = parse_agent_document(content)
    except SchemaValidationError as error:
        return ValidationReport((ValidationIssue("AGENT.md", "markdown", str(error)),))
    return ValidationReport(tuple(_front_matter_issues(front_matter, record, registry_schema) + _heading_issues(headings)))


def validate_agent_config(content: str, record: RepositoryRecord, registry_schema: int = 1) -> ValidationReport:
    """Compatibility name for strict AGENT document validation."""
    return validate_agent_markdown(content, record, registry_schema)


def _render_body(record: RepositoryRecord, skills: Iterable[SkillReference], hooks: Iterable[HookReference]) -> list[str]:
    skill_lines = _dependency_lines("skill", (item.id for item in skills))
    hook_lines = _dependency_lines("hook", (item.id for item in hooks))
    return [
        "# AGENT.md", "", "## Scope", "This file is the global agent policy for the registered repository.", "",
        "## Precedence", "The global registry is the sole authority for managed agent configuration.", "",
        "## Repository identity", f"- Repository ID: {record.repository_id}", f"- Git remote: {record.git_remote}", f"- Local path: {record.local_path}", "",
        "## Required behavior", "Follow this policy and fail closed when its registry metadata is invalid.", "",
        "## Architecture and coding standards", "Use the repository architecture and keep changes focused, typed, and tested.", "",
        "## Verification", "Run the focused checks and the repository's complete quality gates.", "",
        "## Skills", *skill_lines, "", "## Hooks", *hook_lines, "",
        "## Security and secrets", "Never disclose credentials or persist secret environment values.", "",
        "## Change policy", "Change this managed configuration only through registry operations.", "",
    ]


def _dependency_lines(kind: str, identifiers: Iterable[str]) -> list[str]:
    values = tuple(identifiers)
    return [f"- {kind}: {identifier}" for identifier in values] or [f"- No global {kind}s selected."]


def _split_front_matter(content: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if not isinstance(content, str) or not content.startswith("---\n"):
        raise SchemaValidationError("AGENT.md must begin with YAML-like front matter")
    lines = tuple(content.splitlines())
    try:
        end = lines.index("---", 1)
    except ValueError as error:
        raise SchemaValidationError("front matter is missing its closing delimiter") from error
    return lines[1:end], lines[end + 1 :]


def _parse_front_matter(lines: tuple[str, ...]) -> AgentConfigFrontMatter:
    values = _front_matter_values(lines)
    if tuple(values) != _FRONT_MATTER_FIELDS:
        raise SchemaValidationError("front matter fields are incomplete or out of order")
    schema = _parse_version(values["registrySchema"], "registrySchema")
    config_version = _parse_version(values["configVersion"], "configVersion")
    last_reviewed = parse_utc_timestamp(values["lastReviewed"])
    if last_reviewed is None:
        raise SchemaValidationError("lastReviewed must be a UTC timestamp with Z suffix")
    return AgentConfigFrontMatter(schema, values["repositoryId"], values["gitRemote"], config_version, last_reviewed)


def _front_matter_values(lines: tuple[str, ...]) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in lines:
        key, value = _parse_front_matter_line(line)
        if key not in _FRONT_MATTER_FIELDS or key in values:
            raise SchemaValidationError(f"invalid or duplicate front matter field: {key}")
        values[key] = value
    return values


def _parse_front_matter_line(line: str) -> tuple[str, str]:
    if ":" not in line:
        raise SchemaValidationError("front matter lines must contain a key and value")
    key, value = line.split(":", 1)
    if not value.strip():
        raise SchemaValidationError(f"front matter field {key} must be nonempty")
    return key, value.strip()


def _parse_version(value: str, field: str) -> int:
    try:
        return int(value)
    except ValueError as error:
        raise SchemaValidationError(f"{field} must be an integer") from error


def _parse_headings(lines: tuple[str, ...]) -> tuple[str, ...]:
    headings: list[str] = []
    for line in lines:
        heading = _parse_heading_line(line)
        if heading is not None:
            headings.append(heading)
    return tuple(headings)


def _parse_heading_line(line: str) -> str | None:
    match = _HEADING.fullmatch(line)
    if match is None:
        return None
    return _heading_text(len(match.group(1)), match.group(2), line)


def _heading_text(level: int, text: str, line: str) -> str | None:
    if level == 1 and text == "AGENT.md":
        return None
    if level != 2 or text not in _REQUIRED_HEADINGS:
        raise SchemaValidationError(f"invalid heading: {line}")
    return text


def _front_matter_issues(front_matter: AgentConfigFrontMatter, record: RepositoryRecord, registry_schema: int) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if front_matter.registry_schema != registry_schema:
        issues.append(ValidationIssue("registrySchema", "mismatch", "registrySchema does not match registry"))
    if front_matter.repository_id != record.repository_id:
        issues.append(ValidationIssue("repositoryId", "mismatch", "repositoryId does not match record"))
    if front_matter.git_remote != record.git_remote:
        issues.append(ValidationIssue("gitRemote", "mismatch", "gitRemote does not match record"))
    if front_matter.config_version != 1:
        issues.append(ValidationIssue("configVersion", "version", "configVersion must be 1"))
    return issues


def _heading_issues(headings: tuple[str, ...]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for heading in _REQUIRED_HEADINGS:
        count = headings.count(heading)
        if count == 0:
            issues.append(ValidationIssue(f"heading:{heading}", "missing-heading", "required heading is missing"))
        elif count > 1:
            issues.append(ValidationIssue(f"heading:{heading}", "duplicate-heading", "heading is duplicated"))
    return issues
