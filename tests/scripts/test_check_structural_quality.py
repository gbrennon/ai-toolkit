from pathlib import Path

from scripts.check_structural_quality import StructuralQualityChecker


def test_python_file_with_multiple_classes_fails(tmp_path: Path) -> None:
    path = tmp_path / "services.py"
    path.write_text("class First:\n    pass\n\nclass Second:\n    pass\n", encoding="utf-8")

    result = StructuralQualityChecker(path).check()

    assert result == 1


def test_python_constructor_with_six_dependencies_fails(tmp_path: Path) -> None:
    path = tmp_path / "service.py"
    path.write_text(
        "class Service:\n"
        "    def __init__(self, one, two, three, four, five, six):\n"
        "        self.value = one\n",
        encoding="utf-8",
    )

    result = StructuralQualityChecker(path).check()

    assert result == 1


def test_rust_super_visibility_fails(tmp_path: Path) -> None:
    path = tmp_path / "service.rs"
    path.write_text("struct Service;\n\nimpl Service {\n    pub(super) fn run(&self) {}\n}\n", encoding="utf-8")

    result = StructuralQualityChecker(path).check()

    assert result == 1



def test_post_init_state_construction_passes(tmp_path: Path) -> None:
    path = tmp_path / "value.py"
    path.write_text(
        "from dataclasses import dataclass\n\n"
        "@dataclass\nclass Value:\n"
        "    value: int\n\n"
        "    def __post_init__(self):\n"
        "        self.value = int(self.value)\n",
        encoding="utf-8",
    )

    result = StructuralQualityChecker(path).check()

    assert result == 0


def test_regular_method_state_mutation_fails(tmp_path: Path) -> None:
    path = tmp_path / "value.py"
    path.write_text(
        "class Value:\n"
        "    def update(self, value):\n"
        "        self.value = value\n",
        encoding="utf-8",
    )

    result = StructuralQualityChecker(path).check()

    assert result == 1

