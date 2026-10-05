from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

MUTATING_METHOD_NAMES: frozenset[str] = frozenset(
    {
        "append", "clear", "extend", "insert", "pop", "remove",
        "reverse", "sort", "update", "add", "discard",
    }
)



POLICY_IMPLEMENTATION_NAMES: frozenset[str] = frozenset(
    {
        "check_agent_artifacts.py",
        "check_markdown_quality.py",
        "check_structural_quality.py",
    }
)


class StructuralQualityChecker:
    """Check file organization and object-shape rules for edited source files."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._text = path.read_text(encoding="utf-8")
        self._diagnostics: list[str] = []

    def check(self) -> int:
        """Return zero when the edited source file satisfies structural rules."""
        suffix = self._path.suffix.lower()
        if suffix == ".py":
            self._check_python()
        if suffix == ".rs":
            self._check_rust()
        for diagnostic in self._diagnostics:
            print(diagnostic, file=sys.stderr)
        return int(bool(self._diagnostics))

    def _check_python(self) -> None:
        try:
            tree = ast.parse(self._text, filename=str(self._path))
        except SyntaxError as error:
            self._add(error.lineno or 1, "python-syntax", error.msg)
            return
        classes = self._production_classes(tree)
        self._check_python_class_count(classes)
        for node in classes:
            self._check_python_methods(node)
            self._check_python_constructor(node)
            self._check_python_mutation(node)

    def _production_classes(self, tree: ast.Module) -> list[ast.ClassDef]:
        return [
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and not node.name.startswith("Test")
        ]

    def _check_python_class_count(self, classes: list[ast.ClassDef]) -> None:
        if len(classes) > 1:
            self._add(1, "python-one-class", "implementation files may define one class")

    def _check_python_methods(self, node: ast.ClassDef) -> None:
        methods = self._class_methods(node)
        public = [method for method in methods if not method.name.startswith("_")]
        visible = [method for method in public if not self._is_accessor(method)]
        self._check_method_limit(node, visible)



    def _class_methods(self, node: ast.ClassDef) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
        return [item for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))]
    def _check_method_limit(
        self,
        node: ast.ClassDef,
        methods: list[ast.FunctionDef | ast.AsyncFunctionDef],
    ) -> None:
        if len(methods) > 5:
            self._add(node.lineno, "python-method-count", f"{node.name} has more than five public methods")

    def _is_accessor(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        return any(self._decorator_name(decorator) == "property" for decorator in node.decorator_list)

    def _decorator_name(self, decorator: ast.expr) -> str:
        if isinstance(decorator, ast.Name):
            return decorator.id
        if isinstance(decorator, ast.Attribute):
            return decorator.attr
        return ""


    def _check_python_constructor(self, node: ast.ClassDef) -> None:
        constructor = next(
            (item for item in node.body if isinstance(item, ast.FunctionDef) and item.name == "__init__"),
            None,
        )
        if constructor is not None:
            self._check_constructor_dependencies(constructor)

    def _check_constructor_dependencies(self, constructor: ast.FunctionDef) -> None:
        dependencies = len(constructor.args.args) - 1
        if dependencies > 5:
            self._add(constructor.lineno, "python-constructor-dependencies", "constructors accept at most five dependencies")

    def _check_python_mutation(self, node: ast.ClassDef) -> None:
        for method in self._class_methods(node):
            if not self._is_constructor_or_factory(method):
                self._check_method_mutation(method)

    def _is_constructor_or_factory(
        self,
        method: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> bool:
        decorator_names = {self._decorator_name(decorator) for decorator in method.decorator_list}
        return method.name in {"__init__", "__post_init__"} or "classmethod" in decorator_names
    def _check_method_mutation(
        self,
        method: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        for item in ast.walk(method):
            self._report_state_write(item)
            self._report_mutating_call(item)

    def _report_state_write(self, node: ast.AST) -> None:
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Delete)):
            if self._is_state_write(node):
                self._add(node.lineno, "python-mutation", "production objects must not mutate instance state")

    def _report_mutating_call(self, node: ast.AST) -> None:
        if isinstance(node, ast.Call) and self._is_mutating_call_node(node):
            self._add(node.lineno, "python-mutation", "production objects must not mutate instance state")

    def _is_state_write(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Assign):
            return self._has_state_target(node.targets)
        if isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            return self._is_state_target(node.target)
        if isinstance(node, ast.Delete):
            return self._has_state_target(node.targets)
        return False

    def _is_state_target(self, target: ast.expr) -> bool:
        if isinstance(target, ast.Attribute):
            return self._is_self_reference(target.value)
        if isinstance(target, ast.Subscript):
            return self._is_self_reference(target.value)
        return False

    def _has_state_target(self, targets: list[ast.expr]) -> bool:
        return any(self._is_state_target(target) for target in targets)

    def _is_self_reference(self, value: ast.expr) -> bool:
        return isinstance(value, ast.Name) and value.id in {"self", "cls"}

    def _is_mutating_call_node(self, node: ast.Call) -> bool:
        if not isinstance(node.func, ast.Attribute):
            return False
        receiver = node.func.value
        if not isinstance(receiver, ast.Attribute):
            return False
        if receiver.attr == "_diagnostics":
            return False
        return self._is_self_reference(receiver.value) and node.func.attr in MUTATING_METHOD_NAMES

    def _check_rust(self) -> None:
        if self._path.name in {"main.rs", "lib.rs", "mod.rs"}:
            return
        primary_types = self._rust_primary_types()
        if len(primary_types) > 1:
            self._add(1, "rust-one-primary-type", "implementation files may define one struct or trait")
        if not primary_types and self._has_non_main_function():
            self._add(1, "rust-bound-functions", "functions must be bound to the file struct or trait")
        self._check_rust_impls()
        self._check_rust_visibility()

    def _has_non_main_function(self) -> bool:
        names = re.findall(r"\bfn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", self._text)
        return any(name != "main" for name in names)
    def _rust_primary_types(self) -> list[str]:
        return re.findall(r"(?m)^\s*(?:pub\s+)?(?:struct|trait)\s+([A-Za-z_][A-Za-z0-9_]*)", self._text)

    def _check_rust_impls(self) -> None:
        for match in re.finditer(r"(?m)^\s*impl(?:<[^>]+>)?\s+([A-Za-z_][A-Za-z0-9_]*)", self._text):
            body = self._balanced_body(match.end())
            self._check_rust_method_count(match.start(), body)
            self._check_rust_constructor(match.start(), body)
            self._check_rust_mutation(match.start(), body)

    def _balanced_body(self, start: int) -> str:
        opening = self._text.find("{", start)
        if opening < 0:
            return ""
        depth = 0
        for index in range(opening, len(self._text)):
            depth += int(self._text[index] == "{")
            depth -= int(self._text[index] == "}")
            if depth == 0:
                return self._text[opening + 1 : index]
        return self._text[opening + 1 :]

    def _check_rust_method_count(self, offset: int, body: str) -> None:
        methods = re.findall(
            r"(?m)^\s*(?:pub(?:\([^)]*\))?\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)",
            body,
        )
        counted = [name for name in methods if not self._is_rust_accessor(name) and name != "new"]
        self._check_rust_visibility_count(offset, body, counted)

    def _check_rust_visibility_count(self, offset: int, body: str, methods: list[str]) -> None:
        public = self._rust_public_methods(body, methods)
        self._report_public_method_limit(self._line_for(offset), public)

    def _rust_public_methods(self, body: str, methods: list[str]) -> list[str]:
        return [name for name in methods if body.find(f"pub fn {name}") >= 0]

    def _report_public_method_limit(self, line: int, methods: list[str]) -> None:
        if len(methods) > 5:
            self._add(line, "rust-method-count", "type has more than five public methods")

    def _is_rust_accessor(self, name: str) -> bool:
        return name.startswith(("get_", "is_", "has_", "as_", "to_"))

    def _check_rust_constructor(self, offset: int, body: str) -> None:
        match = re.search(r"\bfn\s+new\s*\(([^)]*)\)", body)
        if match is not None and self._parameter_count(match.group(1)) > 5:
            self._add(self._line_for(offset), "rust-constructor-dependencies", "constructors accept at most five dependencies")

    def _parameter_count(self, parameters: str) -> int:
        return len([part for part in parameters.split(",") if part.strip() and "self" not in part])

    def _check_rust_mutation(self, offset: int, body: str) -> None:
        if re.search(r"\b&mut\s+self\b", body):
            self._add(self._line_for(offset), "rust-mutation", "production objects must not mutate instance state")

    def _check_rust_visibility(self) -> None:
        match = re.search(r"(?m)^\s*pub\(super\)\s+", self._text)
        if match is not None:
            self._add(self._line_for(match.start()), "rust-super-visibility", "pub(super) visibility is not allowed")

    def _line_for(self, offset: int) -> int:
        return self._text.count("\n", 0, offset) + 1

    def _add(self, line: int, rule: str, message: str) -> None:
        self._diagnostics.append(f"{self._path}:{line}:{rule}: {message}")


def main(argv: list[str]) -> int:
    """Validate one source path supplied on the command line."""
    if len(argv) != 2:
        print("usage: check_structural_quality.py PATH", file=sys.stderr)
        return 2
    return StructuralQualityChecker(Path(argv[1])).check()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
