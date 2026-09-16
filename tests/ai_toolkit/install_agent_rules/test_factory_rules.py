from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

RULES_PATH = Path(__file__).parents[3] / "agent_rules" / "04-code-writing-style.md"


class TestFactoryRules:
    def test_code_writing_rules_define_portable_factory_guidance(self) -> None:
        content = RULES_PATH.read_text(encoding="utf-8")

        assert "Use a class-level factory only when it returns an instance" in content
        assert "Use an instance method when a dedicated factory class" in content
        assert "Never use a static method as a factory" in content
        assert "annotate a same-class class-level factory return with `Self`" in content
        assert "equivalent same-class return-type rule in Rust, Scala" in content
        assert "check-code-quality" not in content
