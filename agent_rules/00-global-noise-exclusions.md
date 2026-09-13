# General Purpose Noise Exclusions

Exclude build artifacts, cache directories, dependency caches, generated files,
and OS-level noise that clutter context and waste tokens. These patterns are
language-agnostic; language-specific excludes live in per-project rules.

## Patterns to Always Ignore

### Build Output Directories
- `build/`
- `dist/`
- `out/`
- `bin/`
- `obj/`
- `lib/`
- `release/`
- `debug/`
- `target/`
- `coverage/`
- `artifacts/`

### Compiled Bytecode and Object Files
- `*.class`
- `*.pyc`
- `*.pyo`
- `*.o`
- `*.obj`
- `*.a`
- `*.lib`
- `*.so`
- `*.dylib`
- `*.dll`

### Compiled Artifacts (JARs, Bundles, Binaries)
- `*.jar`
- `*.war`
- `*.ear`
- `*.gem`
- `*.rpm`
- `*.deb`
- `*.tgz` (packaged outputs only)

### Package Manager Caches
- `node_modules/`
- `vendor/`
- `.npm/`
- `.pnpm-store/`
- `.yarn/`
- `bower_components/`
- `.gradle/`
- `.m2/` (partial — keep only dependency cache, not source)
- `.bundle/`
- `Pods/`
- `.cargo/`

### Dependency and Lockfile Artifacts
- `*.lock` (dependency lockfiles unless required for reproducibility)
- `vendor/bundle/`
- `.nuget/`

### Test and Coverage Caches
- `.pytest_cache/`
- `.coverage`
- `htmlcov/`
- `.tox/`
- `.mypy_cache/`
- `.nyc_output/`
- `tmp/`
- `test-results/`

### IDE and Editor
- `.vscode/`
- `.idea/`
- `*.swp`
- `*.swo`
- `*~`
- `.project`
- `.classpath`
- `.settings/`

### Logs and Temporary
- `*.log`
- `logs/`
- `tmp/`
- `temp/`
- `.tmp/`
- `*.pid`

### OS-Level
- `.DS_Store`
- `.Thumbs.db`
- `.AppleDouble/`
- `.LSOverride`

### Environment and Local Configuration
- `.env`
- `.env.*`
- `!.env.example`
- `.venv/`
- `venv/`
- `env/`

### Virtual Environments (language-agnostic)
- `.venv/`
- `venv/`
- `ENV/`
- `__pypackages__/`
