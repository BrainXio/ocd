---
name: swift
description: Write, refactor, and audit Swift code with strict concurrency, modern idioms, and SwiftLint gates. Use when creating, reviewing, or fixing Swift files, packages, or concurrency code.
argument-hint: "[file path or 'audit' or 'concurrency']"
---

# Swift Skill

You are a Swift expert who writes safe, concurrent, modern Swift following these conventions.

## Mandatory Rules

- Target Swift 5.9+ — use `if let`/`guard let`, `async`/`await`, `some`/`any` opaque types
- Every function must have parameter labels and return type annotations — no implicit `Void` returns on public APIs
- All public types must have documentation comments (`///`)
- Run `swiftlint` with zero warnings — all rules enforced

## Critical Rules

### Concurrency

- Use `async`/`await` for asynchronous work — never callback chains or `DispatchQueue.async` for new code
- Use `actor` for shared mutable state — never protect shared state with locks manually
- Use `Sendable` conformance to mark types safe for concurrent access
- Use `nonisolated` to opt out of actor isolation where needed
- Use structured concurrency (`TaskGroup`) over unstructured (`Task { }`) when the work has a clear scope
- Use `withCheckedContinuation` only to bridge callback-based APIs — never as a primary pattern
- Use `@MainActor` for UI-bound types — never call UI code from a background context
- Use `async let` for concurrent child tasks when results are consumed independently

### Optionals and Error Handling

- Use `guard let` for early returns — avoid pyramid of doom (nested `if let`)
- Use `try?` only when the error is truly unimportant — never silently swallow errors in production code
- Use custom `Error` enums with descriptive associated values — never use `NSError`
- Use `Result` type for async APIs that can fail — propagate errors with `try`/`catch`
- Use `??` for default values: `let name = optional ?? "unknown"`
- Use `optional.map {}` and `optional.flatMap {}` for transformations — avoid `if let` when a simple transform suffices
- Never force-unwrap (`!`) except in `@IBOutlet` connections and unit tests — use `guard let`, `if let`, or `??`

### Types and Protocols

- Use `struct` by default — use `class` only when reference semantics are needed (identity, inheritance, Objective-C interop)
- Use `enum` with associated values for state machines and result types
- Use `protocol` with `extension` for default implementations — avoid class inheritance for behavior sharing
- Use `some` for opaque return types, `any` for existential types — be explicit about variance
- Use `associatedtype` in protocols for generic requirements
- Use `Codable` for serialization — avoid manual JSON parsing
- Use `Hashable` and `Equatable` automatic synthesis where possible — only implement manually when custom logic is needed

### Collections and Functional Patterns

- Use `map`, `filter`, `reduce`, `compactMap`, `flatMap` — prefer functional transforms over `for` loops
- Use `Set` for uniqueness, `Dictionary` for lookups — never use `.contains()` on an unsorted `Array` for membership checks
- Use `async let` or `TaskGroup` for parallel collection operations — never `DispatchQueue.concurrentPerform`
- Use `Collection` protocol constraints in generic functions — avoid over-constraining to `Array`
- Use slice operations (`dropFirst`, `dropLast`, `prefix`, `suffix`) instead of index arithmetic

### Memory and Performance

- Use `weak` for delegate patterns to avoid retain cycles — never `unowned` unless the lifetime is guaranteed
- Use `[weak self]` in closures that capture `self` — never strong captures in long-lived closures
- Use `lazy var` for expensive one-time initialization
- Use `@autoclosure` for assertions and expensive conditions: `assert(filesize > 0)`
- Profile with Instruments before optimizing — never guess at performance problems
- Use `inout` for value-type mutations in functions — avoid copying large structs unnecessarily

## Linting / Formatting

```bash
# Lint
swiftlint lint --strict

# Format (if SwiftFormat is available)
swiftformat .
```

## Anti-Patterns to Avoid

- Force-unwrap (`!`) outside `@IBOutlet` and tests — use `guard let`, `if let`, or `??`
- `DispatchQueue.main.async` in new code — use `@MainActor` and `async`/`await`
- `Any` type — use generic constraints or `some`/`any` opaque types
- Singleton pattern without justification — use dependency injection instead
- God objects / massive view controllers — use MVVM, coordinators, or clean architecture
- Stringly-typed APIs (`NotificationCenter.default.post(name: Notification.Name("..."))`) — use typed notifications or delegates
- `override` without `final` on classes that shouldn't be subclassed — mark as `final` by default
- `try!` — always use `try` with `catch` or `try?` with error handling
