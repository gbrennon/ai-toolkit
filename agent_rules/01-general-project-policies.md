# General Project Policies

Project-agnostic guidelines for context management and file handling.

## Context Optimization

### Do Read (High Signal)
- `src/`, `lib/`, `app/` — core application code
- `tests/`, `test/` — test files (validate test pyramid)
- `README.md` — project overview
- `ARCHITECTURE.md` — design documentation
- `.github/workflows/*.yml` — CI/CD pipeline definitions (not logs)
- `Makefile`, `justfile`, `Taskfile` — build tasks
- `pyproject.toml`, `Cargo.toml`, `go.mod`, `package.json`, `Gemfile`,
  `pom.xml` — dependency manifests
- `.env.example` — configuration reference (not secrets)
- `docker-compose.yml`, `Dockerfile` — deployment configuration

### Do Not Read (Low Signal, High Noise)
- Generated files (`.pyc`, `.o`, `.class`, etc.)
- Dependency caches (`node_modules/`, `venv/`, `vendor/`, `target/`)
- Lock files (often 1–5MB each: `package-lock.json`, `yarn.lock`, `Cargo.lock`)
- IDE metadata (`.vscode/`, `.idea/`)
- Build artifacts (`build/`, `dist/`, `out/`, `target/`)
- Log files (`*.log`)
- Temporary files (`tmp/`, `temp/`, `.tmp/`)

## Code Reading Strategy

### When asked "explain this project"
1. Read `README.md` or `ARCHITECTURE.md` first
2. Map hexagonal/DDD layers: `domain/`, `application/`, `infrastructure/`, `presentation/`
3. Identify entry point (`main.py`, `lib.rs`, `main.go`, `Application.java`, etc.)
4. Trace one happy path through the codebase
5. Do NOT read all files — focus on structure and key abstractions

### When asked "review this code"
1. Read only the files mentioned
2. Check SOLID principles adherence
3. Validate test coverage (test pyramid)
4. Look for tight coupling, hidden dependencies
5. Suggest refactoring if decoupling improves testability

### When asked "fix this error"
1. Read the error stacktrace first
2. Navigate to the error source
3. Read relevant test files to understand intent
4. Avoid reading unrelated code

## File Exclusion Syntax

Rules use `.gitignore`-style patterns:
- `dir/` → exclude directory and contents recursively
- `*.ext` → exclude by file extension
- `**/pattern` → match pattern at any depth
- `!pattern` → whitelist/exception (keep this file)
- Lines starting with `#` → comments

## Testing Philosophy

### Expected Structure (Test Pyramid)
- **Unit tests (Domain & Application):** Fast, no I/O, explicit fakes
- **Integration tests (Infrastructure & Presentation):** Against real
  infrastructure, validate contracts
- **End-to-end (Presentation):** Validate full user flow

**Should verify:**
- Domain logic has unit tests (no mocking frameworks, state-based)
- Infrastructure has integration tests (real containers, databases, APIs)
- Presentation has E2E tests (real browser, real user actions)
- Test-to-code ratio is reasonable (~1:1 to 2:1)

### Code Organization for Tests
- `tests/unit/` — unit tests (domain, application)
- `tests/integration/` — integration tests (infrastructure)
- `tests/e2e/` — end-to-end tests (presentation)
- Avoid `test_*` or `*_test` files scattered in source tree — keep tests under the test directories

## Hexagonal Architecture Validation

When reviewing a project, validate:
1. **Domain layer** — no infrastructure imports, no HTTP/DB/external APIs
2. **Application layer** — orchestrates domain, depends only on domain + input ports
3. **Infrastructure layer** — implements ports, touches I/O (HTTP, DB, file system)
4. **Presentation layer** — CLI, API routes, validates user input; depends on application

**Red flags:**
- Domain imports infrastructure (tight coupling)
- Application imports presentation (reversed dependency)
- No clear port/adapter boundaries
- Ports containing concrete logic or state (ports must be pure contracts)
- Direct database queries in domain logic

## Language-Specific Rules

Rules load in order:
1. `00-global-noise-exclusions.md` (universal patterns)
2. Language-specific rules (e.g., `lang-python.md`, `lang-rust.md`, if the project adds them)
3. Project overrides (per-project exceptions)

**To extend:** Create a language-specific or project-override rules file in the rules directory.

## Performance Tips

- **Context budget exceeded?** → Narrow the request scope (ask about one layer,
  not the whole project)
- **Slow response?** → Check if large files (>1MB) are being read; whitelist them in overrides
- **Noisy results?** → Add more patterns to project-specific exclusions
- **Want to debug rules?** → "list all excluded patterns and explain why"

## Secrets & Security

**Never read:**
- `.env` files with real values (only `.env.example`)
- `secrets/`, `.secrets/`
- Private keys (`*.pem`, `*.key`)
- API keys in config files
- SSH configs, credentials

**Always use:**
- Environment variable references in code
- `12-factor app` style config (read from env, not files)
