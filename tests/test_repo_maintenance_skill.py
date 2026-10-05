from pathlib import Path


SKILL = Path("skills/repo-maintenance.md").read_text()
PR_INTERACTION = Path("skills/pr-interaction.md").read_text()


def test_maintenance_delegates_forge_operations() -> None:
    assert "pr-interaction" in SKILL
    assert "forge-specific pull-request operations" in SKILL
    assert "forge-specific command details" not in SKILL


def test_maintenance_requires_synchronization_before_pr_work() -> None:
    assert "git fetch origin" in SKILL
    assert "DEFAULT_BRANCH=" in SKILL
    assert "git merge-base --is-ancestor" in SKILL
    assert "git status --porcelain" in SKILL
    assert "git branch --show-current" in SKILL
    assert "git worktree list" in SKILL
    assert "Before opening or updating a pull request" in SKILL
    assert "advances while the PR is open" in SKILL


def test_maintenance_defines_autonomous_pr_entry() -> None:
    assert "autonomous" in SKILL
    assert "If none exists" in SKILL
    assert "push the\nfeature branch" in SKILL
    assert "open one against the default branch" in SKILL
    assert "motivation" in SKILL
    assert "validation" in SKILL
    assert "out-of-scope" in SKILL


def test_maintenance_requires_review_triage_and_ci() -> None:
    assert "every finding and suggestion" in SKILL
    assert "Create a tracking issue" in SKILL
    assert "Dismiss it with a reason" in SKILL
    assert "Every configured CI check" in SKILL
    assert "CI is failing, pending, unavailable, or missing" in SKILL


def test_maintenance_tracks_post_merge_failures_and_cleanup() -> None:
    assert "After merging" in SKILL
    assert "terminal state" in SKILL
    assert "two additional" in SKILL
    assert "inspect logs" in SKILL
    assert "follow-up issue" in SKILL
    assert "worktree" in SKILL
    assert "prune" in SKILL


def test_pr_interaction_owns_forge_selection_and_merge_commands() -> None:
    assert "forge-detect --cli" in PR_INTERACTION
    assert "command -v \"$FORGE_CLI\"" in PR_INTERACTION
    assert '"$FORGE_CLI" --help' in PR_INTERACTION
    assert '"$FORGE_CLI" pr --help' in PR_INTERACTION
    assert "API\nadapter" in PR_INTERACTION
    assert "branch-deletion flag" in PR_INTERACTION


def test_pr_interaction_owns_review_queries_and_triage() -> None:
    assert "Pull-request reviews" in PR_INTERACTION
    assert "Commit statuses and workflow runs" in PR_INTERACTION
    assert "create issue <suggestion-id-prefix-1>" in PR_INTERACTION
    assert "dismiss <suggestion-id-prefix-1>" in PR_INTERACTION
    assert "Do not create duplicate issues" in PR_INTERACTION


def test_skill_sources_have_no_merge_conflict_markers() -> None:
    for skill in (SKILL, PR_INTERACTION):
        assert "<<<<<<<" not in skill
        assert "=======" not in skill
        assert ">>>>>>>" not in skill
