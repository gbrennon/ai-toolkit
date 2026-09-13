# Architecture Guidance

Enforce architectural decisions and prevent structural drift. These rules apply
when writing, reviewing, or refactoring any code in the project.

## Single Responsibility at the File Level

### One Contract Per File

- Never place multiple unrelated abstractions (interfaces, protocols, ABCs) in
  the same file
- Never implement multiple domain services, use cases, or handlers in a single
  file
- Never mix domain logic with infrastructure logic in the same file — each file
  belongs to exactly one architectural layer
- Split a file the moment it grows to serve two distinct concerns or two
  different callers

### Module-Like Files Are Forbidden

- Never create "module" files that re-export unrelated symbols from different
  subsystems just for convenience
- Never create "barrel" files that aggregate public APIs from across layers —
  each layer manages its own public surface
- Package initializers, like `__init__.py`, `mod.rs`, `package-info.java`, and
  other entry-module files, should ONLY re-export without logic. Re-export only
  the symbols that form the immediate package's public contract, and only from
  within that same package

## Ports and Adapters (Hexagonal Architecture)

### Always Define a Contract First

- When the project applies ports and adapters, every external boundary must be
  defined as a port (interface, protocol, or ABC) in the domain or application
  layer
- Always write the port before writing any adapter that implements it
- Never let infrastructure code define the contract — the inner layer owns the
  abstraction

### Adapters Stay in Infrastructure

- All concrete implementations of ports belong in the infrastructure layer
- Never import infrastructure modules (HTTP clients, database drivers, file I/O,
  external SDKs) into domain or application code
- Adapters must be injected through the port — never instantiated directly in
  business logic

### Contract Verification

- Every port must be testable through a fake or stub implementation without any
  real infrastructure
- Every adapter must have an integration test that verifies it satisfies the
  port contract against a real dependency

## Respect Established Principles

### Detect and Follow Project Conventions

- Before writing code, identify which architectural patterns are already applied
  in the project (hexagonal, CQRS, event sourcing, layered, etc.)
- Never introduce a new architectural pattern that conflicts with an existing
  one
- When in doubt about which pattern applies, default to the one already
  established in the same layer or subsystem

### SOLID is Non-Negotiable

- Every class, module, and function must have a single reason to change
- Prefer extension over modification — use abstractions and composition, not
  conditional branching on type
- Subtypes must be substitutable for their base types without weakening
  preconditions or strengthening postconditions
- Prefer narrow, role-specific interfaces over fat ones — clients must not
  depend on methods they do not use
- Always depend on abstractions, never on concretions — inject dependencies,
  never instantiate collaborators with `new` inside business logic

### Composition Over Inheritance

- Never use inheritance where composition is more appropriate
- Inheritance is acceptable only for true "is-a" relationships with
  substitutability, and only when the base class is designed for extension
- Prefer dependency injection and strategy/decorator patterns over deep
  inheritance hierarchies

### Domain Purity

- Domain objects must carry behavior, not just data — avoid anemic domain models
- Domain logic must never depend on infrastructure (no HTTP, no database, no
  file I/O, no external APIs)
- Prefer immutable data structures and pure functions in the domain layer

## Structural Red Flags

When reviewing or writing code, treat these as violations:

- A file containing both an interface and an unrelated helper function — split
  them
- A domain service importing `requests`, `sqlalchemy`, `boto3`, `axios`,
  `jackson`, or any I/O library — move that logic to an adapter
- A `__init__.py`, `mod.rs`, or package initializer re-exporting symbols from a
  different top-level package — remove the cross-layer dependency
- A class with more than one responsibility or more than ~7 public methods —
  decompose it
- A function that mixes domain rules with infrastructure calls — extract the
  infrastructure behind a port
- Inheritance used to share utility code rather than to model a true subtype
  relationship — refactor to composition