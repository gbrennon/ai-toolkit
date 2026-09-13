# Code Writing Style

Rules for writing readable, self-documenting code.

## NEVER Use Comments — Use Only Expressive Names

- **NEVER write comments anywhere in the codebase**:
  - No inline comments, no block comments, no section headers, no explanatory
    comments, and no commented-out code.
  - Zero comments are permitted. A comment is an admission of failure to write
    expressive code.
  - If code feels difficult to understand without explanation, fix the root
    problem: rename identifiers, extract focused helper functions, simplify
    branching, or introduce dedicated domain types.

- **Use ONLY expressive names**:
  - Code must be 100% self-documenting through precise, intention-revealing names
    for:
    - Constants
    - Variables
    - Functions and methods
    - Classes, protocols, and traits
    - Parameters, return types, and type aliases
  - Expressive naming completely eliminates the need for comments.

## Docstrings That Explain Contract or Behavior

Every public function, method, and class must have a docstring.

### For Interfaces / Abstractions (Protocols, ABCs, Ports)

Write a docstring that explains the **contract** — what the caller can expect
and what the implementer must guarantee:
- Preconditions (if any)
- Postconditions / guarantees
- Who is responsible for what

### For Implementations

Write a docstring that explains the **behavior** — how the implementation
fulfills the contract:
- What this specific implementation does
- Any relevant side effects or resource usage
- Why this approach was chosen (if non-obvious)

### Format

Use the project's standard documentation format (JSDoc,
Google/reStructuredText/NumPy in Python, `///` doc comments in Rust, JavaDoc,
or plain) — follow what the codebase already uses.

## Quantitative Size and Complexity Limits

- **Maximum cyclomatic complexity: 5**. Functions or methods exceeding complexity
  of 5 must be refactored before work is considered complete. Break down complex
  branching into smaller, cohesive functions.
- **Maximum control-flow nesting depth: 2**. Third-level nested `if`, `for`,
  `while`, or match/switch constructs are strictly prohibited. Refactor using
  early returns, guard clauses, and extracted helper functions.
- **Maximum function length: 50 lines**. Keep functions focused on a single
  abstraction level and a single responsibility.
- **Maximum class length: 120 lines**. Decompose larger classes into focused
  collaborators composed together.
- **Maximum file length: 300 lines**. Split the file into smaller, cohesive
  modules the moment it approaches this limit.
- **Maximum line length: 100 characters**. Wrap long lines and never rely on
  horizontal scrolling.

## Compose Over Bulk

- Anything too large must be decomposed, never tolerated:
  - A long line → break it into expressive, single-concern statements.
  - A large class → split it into composed collaborators, each with one
    responsibility.
  - A large file → split it into modules, each owning one contract.
- Prefer many small composed pieces over a few large ones so each unit can be
  grasped at a glance.

## NEVER Implement Setters — Implement Domain Behavior Instead

- **NEVER implement setters**:
  - Prohibit all `set_*` methods, generic setter functions, and raw property
    mutators.
  - Never treat objects or entities as passive bags of data with mutable getters
    and setters.
- **Implement explicit domain behavior**:
  - Model state changes as meaningful, intention-revealing domain actions (e.g.
    `account.activate()`, `order.cancel()`, `cart.apply_discount(coupon)`,
    `user.promote_to_admin()`).
  - Never expose methods like `account.set_status()`, `order.set_state()`, or
    `user.set_role()`.
  - Domain methods must encapsulate state transitions, enforce business
    invariants, and validate rules internally.

## Structural Conventions & Encapsulation

- **Struct field encapsulation**: Struct fields must not be public. Avoid public
  mutable state. Avoid public tuple and unit structs unless strictly
  representing an explicit domain value object.
- **No inline modules**: Place modules and abstractions in their own separate
  files. Follow one contract / abstraction per file.
- **Architectural boundaries**: Domain logic must never import or depend on
  infrastructure or presentation layers. Outer layers depend on inner
  abstractions; domain remains pure.

## Automated Quality Tooling Verification

- Agents must run code quality checks before claiming implementation complete:
  - Run `check-code-quality` (or `lizard -C 5` and `semgrep scan --config
    .semgrep .`) whenever available.
  - Zero violations are permitted in changed or newly created code.

## Strong Typing & Enforced Type Hints

- **Mandatory type annotations on all code and examples**:
  - Every function, method, parameter, return value, variable (where inference
    is non-trivial), and class attribute must be explicitly type-hinted.
  - Never write an example, docstring snippet, or implementation without complete
    type hints.
  - Avoid loose types like `Any`, `unknown`, raw untyped dictionaries/maps, or
    `object`/`Object` unless strictly required at an external boundary.
- **Strongly-typed generics for libraries and reusable abstractions**:
  - Code quality requires strong types everywhere; library interfaces and shared
    components must define strongly-typed generics (e.g. `Generic[T]`,
    `TypeVar`, Rust generic parameters/traits, TypeScript generic constraints).
  - Use bounded generics and Protocols/traits to specify exact behavioral
    expectations at compile time.

## Never Use Ignore Comments or Rules

- **Strict prohibition on ignore comments/rules**:
  - Agents must **NEVER** add or use ignore comments or suppression directives
    (e.g. `# type: ignore`, `# noqa`, `# pyright: ignore`, `# ruff: noqa`,
    `@ts-ignore`, `@ts-nocheck`, `#[allow(...)]`, `/* eslint-disable */`).
  - Ignore comments hide underlying code quality misses, broken contracts, or
    design flaws instead of fixing root causes.
  - When a type checker or linter flags an issue:
    - Fix the underlying type signature, schema, or implementation.
    - Narrow types using proper type guards, pattern matching, or domain
      assertions.
    - Redesign the contract or interface if the current abstraction cannot be
      cleanly typed.
