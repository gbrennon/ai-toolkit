# Markdown Writing Style

Rules for writing readable markdown files: documentation, rule files, and guides.

## Composition Limits

- Maximum line length: 100 characters; wrap prose lines.
- Maximum file length: 300 lines; split the document into composed files the
  moment it approaches this limit.
- Maximum section length: 60 lines; keep each section on a single topic.
- Compose documents from small sections instead of one long wall of prose.

## Structure

- Use a single `#` H1 title naming the document's topic.
- Keep a strict heading hierarchy — `##` sections with `###` subsections — and never skip levels.
- Open the document with a one-sentence scope statement right after the title.
- Write one testable directive per bullet; split any bullet that needs "and".

## Style

- Prefer short bullet lists over long prose paragraphs.
- Use tables only to compare items or enumerate contracts.
- Wrap symbols and paths in inline backticks and code blocks in fenced fences.
- State the prohibition and the replacement behavior together.