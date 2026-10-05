from pathlib import Path


PR_INTERACTION = Path("skills/pr-interaction.md").read_text()
REPO_MAINTENANCE = Path("skills/repo-maintenance.md").read_text()
AGENT_HOOK = Path("skills/agent-hook-pr-review.md").read_text()


def test_pr_interaction_owns_forge_operations() -> None:
    assert "forge-detect --cli" in PR_INTERACTION
    assert "Pull-request reviews" in PR_INTERACTION
    assert "Commit statuses and workflow runs" in PR_INTERACTION
    assert "create issue <suggestion-id-prefix-1>" in PR_INTERACTION
    assert "Inspect the installed merge command" in PR_INTERACTION

def test_repo_maintenance_delegates_pull_request_operations() -> None:
    assert "pr-interaction" in REPO_MAINTENANCE
    assert "forge-specific command details" not in REPO_MAINTENANCE


def test_agent_hook_documents_only_implemented_behavior() -> None:
    assert "current pull-request head before polling begins" in AGENT_HOOK
    assert "incremental backoff" in AGENT_HOOK
    assert "does not implement webhook events" in AGENT_HOOK
    assert "`.agenthookrc` configuration" in AGENT_HOOK
    assert "--auto-update" not in AGENT_HOOK
    assert "--cache-ttl" not in AGENT_HOOK
    assert "--on-new-review" not in AGENT_HOOK
