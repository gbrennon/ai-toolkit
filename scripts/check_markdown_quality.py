from __future__ import annotations

import re
import sys
from pathlib import Path


class MarkdownQualityChecker:
    """Validate focused Markdown documents and report actionable diagnostics."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lines = path.read_text(encoding="utf-8").splitlines()
        self._diagnostics: list[str] = []

    def check(self) -> int:
        """Return zero when the Markdown document satisfies all quality rules."""
        self._check_line_width()
        self._check_file_size()
        self._check_headings()
        self._check_scope_sentence()
        self._check_section_sizes()
        for diagnostic in self._diagnostics:
            print(diagnostic, file=sys.stderr)
        return 1 if self._diagnostics else 0

    def _check_line_width(self) -> None:
        for number, line in enumerate(self._lines, start=1):
            if len(line) > 100:
                self._add(number, "markdown-line-width", "line exceeds 100 characters")

    def _check_file_size(self) -> None:
        if len(self._lines) > 300:
            self._add(1, "markdown-file-size", "split documents longer than 300 lines")

    def _check_headings(self) -> None:
        headings = self._read_headings()
        self._check_heading_count(headings)
        self._check_heading_hierarchy(headings)

    def _read_headings(self) -> list[tuple[int, int]]:
        headings: list[tuple[int, int]] = []
        in_fence = False
        for number, line in enumerate(self._lines, start=1):
            if line.startswith("```"):
                in_fence = not in_fence
            elif not in_fence:
                match = re.match(r"^(#+)\s+", line)
                if match is not None:
                    headings.append((len(match.group(1)), number))
        return headings

    def _check_heading_count(self, headings: list[tuple[int, int]]) -> None:
        if sum(level == 1 for level, _ in headings) != 1:
            self._add(1, "markdown-heading", "document must contain exactly one H1 heading")

    def _check_heading_hierarchy(self, headings: list[tuple[int, int]]) -> None:
        previous = 0
        for level, number in headings:
            if previous and level > previous + 1:
                self._add(number, "markdown-heading-hierarchy", "heading levels must not skip")
            previous = level

    def _check_scope_sentence(self) -> None:
        title_index = self._title_index()
        if title_index is None:
            return
        content = self._first_content_after(title_index)
        if not content or content.startswith("#") or content.startswith(("- ", "* ")):
            self._add(
                title_index + 2,
                "markdown-scope",
                "add one scope sentence immediately after the H1",
            )

    def _title_index(self) -> int | None:
        return next(
            (index for index, line in enumerate(self._lines) if line.startswith("# ")),
            None,
        )

    def _first_content_after(self, title_index: int) -> str:
        return next(
            (line.strip() for line in self._lines[title_index + 1 :] if line.strip()),
            "",
        )

    def _check_section_sizes(self) -> None:
        headings = self._read_headings()
        for index, (level, number) in enumerate(headings):
            if level == 1:
                continue
            end = self._section_end(headings, index, level)
            if end - number + 1 > 60:
                self._add(number, "markdown-section-size", "split sections longer than 60 lines")

    def _section_end(
        self,
        headings: list[tuple[int, int]],
        index: int,
        level: int,
    ) -> int:
        for next_level, number in headings[index + 1 :]:
            if next_level <= level:
                return number - 1
        return len(self._lines)

    def _add(self, line: int, rule: str, message: str) -> None:
        self._diagnostics.append(f"{self._path}:{line}:{rule}: {message}")


def main(argv: list[str]) -> int:
    """Validate one Markdown path supplied on the command line."""
    if len(argv) != 2:
        print("usage: check_markdown_quality.py PATH", file=sys.stderr)
        return 2
    path = Path(argv[1])
    if path.suffix.lower() not in {".md", ".markdown"}:
        return 0
    return MarkdownQualityChecker(path).check()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
