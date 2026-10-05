from pathlib import Path

from scripts.check_markdown_quality import MarkdownQualityChecker


def test_valid_focused_document_passes(tmp_path: Path) -> None:
    path = tmp_path / "guide.md"
    path.write_text("# Guide\n\nThis guide explains the quality gate.\n\n## Rules\n\nKeep files focused.\n", encoding="utf-8")

    result = MarkdownQualityChecker(path).check()

    assert result == 0


def test_document_with_long_line_fails(tmp_path: Path) -> None:
    path = tmp_path / "guide.md"
    path.write_text(f"# Guide\n\n{'x' * 101}\n", encoding="utf-8")

    result = MarkdownQualityChecker(path).check()

    assert result == 1


def test_document_with_skipped_heading_fails(tmp_path: Path) -> None:
    path = tmp_path / "guide.md"
    path.write_text("# Guide\n\nScope.\n\n### Detail\n", encoding="utf-8")

    result = MarkdownQualityChecker(path).check()

    assert result == 1


def test_section_longer_than_sixty_lines_fails(tmp_path: Path) -> None:
    path = tmp_path / "guide.md"
    content = "# Guide\n\nScope.\n\n## Rules\n\n" + "\n".join(["line"] * 60) + "\n"
    path.write_text(content, encoding="utf-8")

    result = MarkdownQualityChecker(path).check()

    assert result == 1


def test_multiple_short_sections_can_exceed_sixty_total_lines(tmp_path: Path) -> None:
    path = tmp_path / "guide.md"
    content = "# Guide\n\nScope.\n\n## First\n\n"
    content += "\n".join(["line"] * 30)
    content += "\n\n## Second\n\n"
    content += "\n".join(["line"] * 30)
    path.write_text(content + "\n", encoding="utf-8")

    result = MarkdownQualityChecker(path).check()

    assert result == 0
