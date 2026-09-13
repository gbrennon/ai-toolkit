# Communication & Workflow

## Language & Tone

### Always Use en-US

- Write all responses, comments, commit messages, and documentation in
  **American English (en-US)**
- Use US spelling conventions: `color` not `colour`, `initialize` not
  `initialise`, `behavior` not `behaviour`

### No Emojis

- Never use emojis in code, commit messages, documentation, or responses
- Communicate using text only

## Code Reading Strategy

### Prefer Interfaces Over Implementations

- When understanding unfamiliar code, start by reading **interfaces, types, and
  abstractions** first
- Only read the concrete implementation of a module or function when you are
  about to **modify or refactor it**
- This conserves context and reduces the surface area held in working memory

Examples of what to prioritize:
- Function/class signatures and their type annotations
- Protocol/interface/abstract class definitions
- Port/adapter contracts
- Public API surfaces of a module

## Modification Workflow

### Always Verify After Changes

- Before declaring any modification complete, **run the verification command**
  appropriate for the project
- Verification includes: test suite execution, type checking, linting — whatever
  the project defines as its quality gate
- Do not assume changes are correct without running the verification step
- If a verification command is not obvious, ask the user what to run