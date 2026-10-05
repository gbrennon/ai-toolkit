from pathlib import Path

from scripts.check_agent_artifacts import AgentArtifactChecker


def test_generated_plan_path_fails(tmp_path: Path) -> None:
    path = tmp_path / "docs" / "superpowers" / "plans" / "plan.md"
    path.parent.mkdir(parents=True)
    path.write_text("# Plan\n", encoding="utf-8")
    rules = tmp_path / "agent-artifacts.txt"
    rules.write_text("docs/superpowers/plans/\n", encoding="utf-8")

    result = AgentArtifactChecker([path], rules, tmp_path).check()
    assert result == 1


def test_authored_document_passes(tmp_path: Path) -> None:
    path = tmp_path / "docs" / "README.md"
    path.parent.mkdir()
    path.write_text("# README\n", encoding="utf-8")
    rules = tmp_path / "agent-artifacts.txt"
    rules.write_text("docs/superpowers/plans/\n", encoding="utf-8")

    result = AgentArtifactChecker([path], rules, tmp_path).check()

    assert result == 0
