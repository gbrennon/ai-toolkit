from pathlib import Path


SKILL = Path("skills/repo-maintenance.md").read_text()


def test_skill_uses_remote_appropriate_forge_cli():
    assert "forge-detect --cli" in SKILL
    assert "tea" not in SKILL
    assert "gh" in SKILL
    assert "fj" in SKILL


def test_skill_requires_post_merge_worktree_cleanup():
    assert "git worktree remove" in SKILL
    assert "git worktree prune" in SKILL
    assert "current cwd" in SKILL
