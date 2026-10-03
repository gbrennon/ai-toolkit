from pathlib import Path


SKILL = Path("skills/repo-maintenance.md").read_text()


def test_skill_uses_remote_appropriate_forge_cli():
    assert "forge-detect --cli" in SKILL
    assert "tea pr" not in SKILL
    assert "gh" in SKILL
    assert "fj" in SKILL


def test_skill_requires_post_merge_worktree_cleanup():
    assert "git worktree remove" in SKILL
    assert "git worktree prune" in SKILL
    assert "current cwd" in SKILL


def test_skill_tracks_post_merge_ci_retries_and_investigates_persistent_failure():
    assert "After merging" in SKILL
    assert "terminal" in SKILL
    assert "rerun" in SKILL
    assert "two additional" in SKILL
    assert "logs" in SKILL
    assert "investigate" in SKILL
    assert "follow-up" in SKILL
    assert "fix" in SKILL


def test_skill_autonomously_pushes_and_opens_missing_pr():
    assert "autonomous" in SKILL
    assert "If no PR exists" in SKILL
    assert "push" in SKILL
    assert "open the PR" in SKILL
    assert "Do not pause for user confirmation" in SKILL


def test_skill_requires_expressive_pr_scope_description():
    assert "expressive" in SKILL
    assert "Motivation" in SKILL
    assert "Changes" in SKILL
    assert "Validation" in SKILL
    assert "Out of scope" in SKILL


def test_skill_defines_reasoned_review_commands():
    assert "create issue <suggestion-id-prefix" in SKILL
    assert "dismiss <suggestion-id-prefix" in SKILL
    assert "prefix" in SKILL
    assert "Do not create an issue for every suggestion" in SKILL
    assert "Do not dismiss a suggestion merely because it is out of scope" in SKILL
    assert "reason" in SKILL.lower()


def test_skill_requires_pre_pr_worktree_synchronization():
    assert "git fetch origin" in SKILL
    assert "DEFAULT_BRANCH=" in SKILL
    assert "git merge-base --is-ancestor" in SKILL
    assert "git status --porcelain            # MUST still be empty after rebase" in SKILL
    assert "git branch --show-current" in SKILL
    assert "git worktree list" in SKILL


def test_skill_places_synchronization_gate_before_push_instruction():
    sync_gate = SKILL.index("Confirm the worktree and branch are in sync")
    push_instruction = SKILL.index("- **Push the feature branch**")

    assert sync_gate < push_instruction


def test_skill_source_has_no_merge_conflict_markers():
    assert "<<<<<<<" not in SKILL
    assert "=======" not in SKILL
    assert ">>>>>>>" not in SKILL


def test_skill_requires_help_driven_merge_commands():
    assert '"$FORGE_CLI" --help' in SKILL
    assert '"$FORGE_CLI" pr --help' in SKILL
    assert "branch-deletion flag" in SKILL
    assert "selected forge's API adapter" in SKILL
    assert "$FORGE_CLI pr merge <number> --delete" not in SKILL


def test_skill_falls_back_to_remote_based_cli_selection():
    assert "command -v forge-detect" in SKILL
    assert 'REMOTE_NAME="${REMOTE:-$(git config --get "branch.$(git branch --show-current).remote"' in SKILL
    assert 'git remote | { IFS= read -r first; printf \'%s\' "$first"; }' in SKILL
    assert "*github.com*) FORGE_CLI=gh" in SKILL
    assert "*codeberg.org*|*forgejo*|*gitea*) FORGE_CLI=fj" in SKILL
    assert 'command -v "$FORGE_CLI"' in SKILL
    assert "uv run forge-detect --cli" not in SKILL


def test_skill_requires_help_driven_cli_subcommands():
    assert '"$FORGE_CLI" --help' in SKILL
    assert '"$FORGE_CLI" pr --help' in SKILL
    assert "supported API adapter" in SKILL
    assert "version-specific flags" in SKILL
    assert "gh pr checks <number>" not in SKILL
    assert "glab ci status" not in SKILL
    assert "$FORGE_CLI pulls <number>" not in SKILL
