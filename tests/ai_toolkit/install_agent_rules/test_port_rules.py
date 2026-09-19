from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

RULES_PATH = Path(__file__).parents[3] / "agent_rules" / "02-architecture-guidance.md"


class TestPortRules:
    def test_architecture_rules_define_ports_as_pure_contracts(self) -> None:
        content = RULES_PATH.read_text(encoding="utf-8")

        assert "Ports Are Pure Contracts" in content
        assert "Define every port strictly as a contract" in content
        assert "never make a port concrete" in content
        assert "Never place executable behavior, state, or concrete method implementations" in content
        assert "refactor the port into a pure contract and move implementation" in content
