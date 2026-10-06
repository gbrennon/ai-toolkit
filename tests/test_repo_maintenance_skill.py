from pathlib import Path


SKILL = Path("skills/repo-maintenance.md").read_text()
PR_INTERACTION = Path("skills/pr-interaction.md").read_text()
GIT_GUIDANCE = Path("agent_rules/07-git-guidance.md").read_text()
FINISHING = Path("skills/finishing-a-development-branch.md").read_text()


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


def test_maintenance_defines_autonomous_scope_boundary() -> None:
    assert "Start from the user's stated scope" in SKILL
    assert "Do not ask for routine confirmation" in SKILL
    assert (
        "Ask a question only when scope is materially missing or contradictory" in SKILL
    )


def test_maintenance_requires_lifecycle_notifications() -> None:
    assert (
        "notifications for the `question`, `complete`, and `error` events" in SKILL
    )
    assert "agent-notify" in SKILL
    assert "visible tmux pane" in SKILL


def test_maintenance_requires_review_triage_and_ci() -> None:
    assert "every finding and suggestion" in SKILL
    assert "Comment `create issue <ids>` on the PR." in SKILL
    assert "Comment `dismiss <ids>` on the PR." in SKILL
    assert "Never\nmanually invoke an issue-creation command" in SKILL
    assert "direct issue-creation\nfallback" in SKILL
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
    assert 'command -v "$FORGE_CLI"' in PR_INTERACTION
    assert '"$FORGE_CLI" --help' in PR_INTERACTION
    assert '"$FORGE_CLI" pr --help' in PR_INTERACTION
    assert "API\nadapter" in PR_INTERACTION
    assert "branch-deletion flag" in PR_INTERACTION


def test_pr_interaction_owns_review_queries_and_triage() -> None:
    assert "Pull-request reviews" in PR_INTERACTION
    assert "Commit statuses and workflow runs" in PR_INTERACTION
    assert "create issue <ids>" in PR_INTERACTION
    assert "dismiss <ids>" in PR_INTERACTION
    assert "`<id1> , <id2> , <id3>`" in PR_INTERACTION
    assert "Never invoke an issue" in PR_INTERACTION
    assert "do not create duplicate issues" in PR_INTERACTION



def test_git_guidance_allows_authorized_forge_merges() -> None:
    assert "Never push directly to `main` or merge locally into `main`." in GIT_GUIDANCE
    assert "Authorized autonomous maintenance" in GIT_GUIDANCE
    assert "merge an approved pull request through\n  the forge" in GIT_GUIDANCE
    assert "review, CI, and synchronization gates pass" in GIT_GUIDANCE



def test_finishing_skill_uses_forge_merge_only() -> None:
    assert "Merge approved pull request through the forge" in FINISHING
    assert "pr-interaction" in FINISHING
    assert "git merge <feature-branch>" not in FINISHING
    assert "Merge locally" not in FINISHING
def test_skill_sources_have_no_merge_conflict_markers() -> None:
    for skill in (SKILL, PR_INTERACTION, GIT_GUIDANCE):
        assert "<<<<<<<" not in skill
        assert "=======" not in skill
        assert ">>>>>>>" not in skill
