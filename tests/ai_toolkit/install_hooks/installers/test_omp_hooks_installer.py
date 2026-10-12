import json
import os
import subprocess
from pathlib import Path

import pytest

from ai_toolkit.install_hooks.installers.omp_hooks_installer import (
    OMP_HOOK_PATH,
    OmpHooksInstaller,
)

pytestmark = pytest.mark.integration


class TestOmpHooksInstaller:
    """Verify OmpHooksInstaller writes self-contained native TS quality hook."""

    def test_create_targets_default_hook_path(self) -> None:
        installer = OmpHooksInstaller.create()

        assert installer.hook_path == OMP_HOOK_PATH

    def test_install_writes_native_omp_hook(self, tmp_path: Path) -> None:
        target = tmp_path / "hooks" / "post" / "quality.ts"

        installed = OmpHooksInstaller.create(target).install()

        assert installed is True
        content = target.read_text(encoding="utf-8")
        assert (
            'import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";'
            in content
        )
        assert 'pi.on("tool_result"' in content
        assert "class CircuitBreakerStore" in content
        assert '"check-code-quality"' in content
        assert "py: true" in content
        assert "md: true" in content

    def test_installed_omp_hook_executes_under_bun_fake_hook_api(
        self, tmp_path: Path
    ) -> None:
        target = tmp_path / "hooks" / "post" / "quality.ts"
        OmpHooksInstaller.create(target).install()
        harness = tmp_path / "omp_harness.mjs"
        harness.write_text(
            f'import hook from "{target.as_posix()}";\n'
            'let h; const calls = [];\n'
            'hook({ on(_e, fn) { h = fn; }, async exec(c, a) {\n'
            '  calls.push(c); return { code: 1, stdout: "", stderr: "err" };\n'
            '} });\n'
            'const ev = { toolName: "edit", input: { path: "b.ts" }, content: [] };\n'
            'const ctx = { cwd: "/tmp", sessionId: "s2" };\n'
            'await h(ev, ctx); const p2 = await h(ev, ctx); const p3 = await h(ev, ctx);\n'
            'console.log(JSON.stringify({ calls: calls.length, p2, p3 }));\n',
            encoding="utf-8",
        )
        env = {
            "PATH": os.environ.get("PATH", ""),
            "AI_TOOLKIT_CIRCUIT_BREAKER_STATE": str(tmp_path / "omp-breaker.json"),
            "AI_TOOLKIT_CIRCUIT_BREAKER_THRESHOLD": "2",
        }

        result = subprocess.run(
            ["bun", str(harness)], cwd="/tmp", capture_output=True, text=True, check=False, env=env
        )

        assert result.returncode == 0
        payload = json.loads(result.stdout.strip())
        assert payload["calls"] == 2
        assert "circuit_breaker_open" in json.dumps(payload["p2"])
        assert "read_file_again_or_request_help" in json.dumps(payload["p3"])

    def test_install_is_deterministic(self, tmp_path: Path) -> None:
        target = tmp_path / "quality.ts"
        installer = OmpHooksInstaller.create(target)

        installer.install()
        first_content = target.read_text(encoding="utf-8")
        installer.install()
        second_content = target.read_text(encoding="utf-8")

        assert first_content == second_content
