# Test Writing Style

Rules for writing tests that are unbiased, well-structured, and readable.
Use expressive names for test classes, tests, parameters, and methods so tests are self-documenting.
No comments, expressive names only.

## What to Test

- Test behavior only, never implementation.
- Assert what the tested code returns in a given scenario, never that a method was called.
- Exercise the code in all possible scenarios.
- Keep tests simple and free of logic.
- Keep the test-quality bar high.

## Test-First Workflow

- Write the failing test before modifying the implementation when behavior changes.

## Test Organization by Language

- Rust: place all tests for a source file inside a single `#[cfg(test)] mod tests` block.
- Python: group tests inside a test class, one class per behavior.
- Other languages: follow the language's standard test-grouping convention.
- Keep each test file small; split it into composed files the moment it grows.

## AAA Structure

Every test is split into three sections a reader can identify at a glance:

1. **Assign** — set up inputs, dependencies, and expected values.
2. **Act** — run the behavior under test with a single action.
3. **Assert** — verify the observed outcome.

Separate each section with exactly one blank line.

```rust
#[test]
fn total_applies_percentage_discount() {
    let cart = cart_with_two_items();

    let total = cart.total_after(discount_of(10));

    assert_eq!(total, 90);
}
```

Each section stays in its own block: never merge the action into the assertion
and never hide the assignment inside the action line.

## Test Doubles

- In unit tests, mock only injectable dependencies.
- For external dependencies, never mock what you do not own: write integration
  tests that inject fake classes.
- Give each fake or stub class exactly one scenario, e.g. one stub class that
  returns an HTTP 400 response.

## Test Coverage

- Never decrease the current test coverage percentage.
- Pure implementations must reach 100% test coverage.
- Implementations with external dependencies must reach at least 80% test coverage.

## Composition Limits

- Apply the same size limits as code: maximum line length of 100 characters,
  maximum class length of 120 lines, and maximum file length of 300 lines.
- Split an oversized test into composed scenarios, one assertion path per test.
- Split an oversized test file by behavior.