from importlib import import_module
from pathlib import Path


def test_all_runtime_modules_are_under_ai_toolkit() -> None:
    root = Path(__file__).parents[1]
    assert not (root / "bin").exists()
    assert not (root / "src" / "cli").exists()
    assert (root / "src" / "ai_toolkit" / "hooks" / "__init__.py").exists()
    assert not (root / "src" / "hooks").exists()
    assert not (root / "src" / "install_hooks").exists()


def test_moved_modules_are_importable_from_ai_toolkit() -> None:
    assert hasattr(import_module("ai_toolkit.hooks.pr_opened_hook"), "PROpenedHook")
    assert hasattr(
        import_module("ai_toolkit.install_hooks.installers.pi_hooks_installer"),
        "install_hooks",
    )
