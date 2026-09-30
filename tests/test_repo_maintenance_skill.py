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


def test_skill_tracks_post_merge_ci_and_retries_once():
    assert "After merging" in SKILL
    assert "terminal" in SKILL
    assert "rerun" in SKILL
    assert "once" in SKILL
    assert "fails again" in SKILL


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
