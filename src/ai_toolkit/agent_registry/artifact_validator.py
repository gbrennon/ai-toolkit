from dataclasses import dataclass

from .dependencies import (
    load_hooks,
    load_skills,
    parse_hook_manifest,
    parse_skill_manifest,
)
from .errors import RegistryError
from .hashing import Sha256Digest
from .json_document_store import JsonDocumentStore
from .markdown import validate_agent_markdown
from .models import RepositoryRecord, ValidationIssue, ValidationReport
from .paths import RegistryPaths
from .repository_paths import RepositoryPaths


@dataclass(frozen=True, slots=True)
class RegistryArtifactValidator:
    """Validate the managed global artifacts for one registry record."""

    paths: RegistryPaths
    store: JsonDocumentStore

    def validate(
        self, record: RepositoryRecord, schema_version: int
    ) -> ValidationReport:
        """Return every independent managed-artifact issue for the record."""
        issues: list[ValidationIssue] = []
        repository = self.paths.repository(record.repository_id)
        if record.agent_config_path != repository.agent_config:
            issues.append(
                ValidationIssue(
                    "agentConfigPath",
                    "path-containment",
                    "agentConfigPath must be the repository ID's global AGENT.md",
                )
            )
        self._validate_agent(record, schema_version, issues)
        self._validate_metadata(record, repository, issues)
        self._validate_dependencies(repository, issues)
        return ValidationReport(tuple(issues))

    def _validate_agent(
        self,
        record: RepositoryRecord,
        schema_version: int,
        issues: list[ValidationIssue],
    ) -> None:
        content_bytes = self._read_agent_bytes(record, issues)
        if content_bytes is None:
            return
        self._validate_agent_digest(record, content_bytes, issues)
        self._validate_agent_content(record, schema_version, content_bytes, issues)

    def _read_agent_bytes(
        self,
        record: RepositoryRecord,
        issues: list[ValidationIssue],
    ) -> bytes | None:
        try:
            return record.agent_config_path.read_bytes()
        except OSError:
            issues.append(
                ValidationIssue("agentConfigPath", "missing", "AGENT.md is unreadable")
            )
            return None

    def _validate_agent_digest(
        self,
        record: RepositoryRecord,
        content_bytes: bytes,
        issues: list[ValidationIssue],
    ) -> None:
        if Sha256Digest.digest_bytes(content_bytes) != record.config_sha256:
            issues.append(
                ValidationIssue(
                    "configSha256",
                    "digest",
                    "AGENT.md bytes do not match configSha256",
                )
            )

    def _validate_agent_content(
        self,
        record: RepositoryRecord,
        schema_version: int,
        content_bytes: bytes,
        issues: list[ValidationIssue],
    ) -> None:
        try:
            content = content_bytes.decode("utf-8")
        except UnicodeDecodeError as error:
            issues.append(ValidationIssue("AGENT.md", "encoding", str(error)))
            return
        issues.extend(validate_agent_markdown(content, record, schema_version).issues)

    def _validate_metadata(
        self,
        record: RepositoryRecord,
        repository: RepositoryPaths,
        issues: list[ValidationIssue],
    ) -> None:
        try:
            metadata = self.store.read(repository.metadata)
        except (OSError, RegistryError) as error:
            issues.append(ValidationIssue("metadata", "metadata", str(error)))
            return
        if metadata != record.to_json():
            issues.append(
                ValidationIssue(
                    "metadata", "metadata", "metadata does not match registry record"
                )
            )

    def _validate_dependencies(
        self,
        repository: RepositoryPaths,
        issues: list[ValidationIssue],
    ) -> None:
        self._validate_skill_dependencies(repository, issues)
        self._validate_hook_dependencies(repository, issues)

    def _validate_skill_dependencies(
        self,
        repository: RepositoryPaths,
        issues: list[ValidationIssue],
    ) -> None:
        try:
            skill_references = parse_skill_manifest(self.store.read(repository.skills))
            load_skills(skill_references, self.paths)
        except (OSError, RegistryError) as error:
            issues.append(ValidationIssue("skills", "dependencies", str(error)))

    def _validate_hook_dependencies(
        self,
        repository: RepositoryPaths,
        issues: list[ValidationIssue],
    ) -> None:
        try:
            hook_references = parse_hook_manifest(self.store.read(repository.hooks))
            load_hooks(hook_references, self.paths)
        except (OSError, RegistryError) as error:
            issues.append(ValidationIssue("hooks", "dependencies", str(error)))
