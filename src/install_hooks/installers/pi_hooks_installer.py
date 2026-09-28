"""
Install Agent Hooks

Registers PR opened hook and other core hooks.
Runs once during project setup.
"""
import os
import shutil
from pathlib import Path

def install_hooks():
    """
    Install all required agent hooks.
    Creates .hooks/ directory and copies hook modules.
    """
    # Define target directories
    hooks_dir = Path(".hooks")
    src_hooks_dir = Path("src/hooks")

    # Ensure .hooks exists
    if not hooks_dir.exists():
        hooks_dir.mkdir(parents=True)
        print(f"[HOOK] Created hooks directory: {hooks_dir}")
    else:
        print(f"[HOOK] Hooks directory already exists: {hooks_dir}")

    # Copy pr_opened_hook.py to .hooks/
    source_file = src_hooks_dir / "pr_opened_hook.py"
    dest_file = hooks_dir / "pr_opened_hook.py"

    try:
        if source_file.exists():
            shutil.copy2(source_file, dest_file)
            print(f"[HOOK] Installed PR opened hook: {dest_file}")
        else:
            raise FileNotFoundError(f"Source file not found: {source_file}")
    except Exception as e:
        print(f"[HOOK] Failed to install hook: {e}")
        return False

    # Write registry file for dynamic loading
    registry_path = hooks_dir / "__registry__.json"
    registry_data = {
        "installed": [
            "pr_opened_hook.py"
        ],
        "version": "0.1.0",
        "last_updated": "2026-09-28"
    }

    with open(registry_path, "w") as f:
        import json
        json.dump(registry_data, f, indent=4)

    print(f"[HOOK] Hook registry created at {registry_path}")

    return True

if __name__ == "__main__":
    success = install_hooks()
    if success:
        print("[HOOK] ✅ All hooks installed successfully.")
    else:
        print("[HOOK] ❌ Failed to install hooks.")
