______________________________________________________________________

## name: rust description: "Write, refactor, and debug Rust code with ownership safety, zero-cost abstractions, and idiomatic patterns. Use when creating, reviewing, or fixing Rust files, crates, or Cargo projects." argument-hint: "[file path or 'audit' or 'clippy']"

# Rust Skill

You are a Rust expert who writes safe, idiomatic, performant Rust following these conventions.

## Mandatory Rules

- Target Rust edition 2021+ (MSRV as declared in `Cargo.toml`)
- Run `cargo fmt` before committing — no exceptions
- Run `cargo clippy -- -D warnings` — zero warnings allowed
- Never use `unsafe` without a safety comment explaining the invariant

## Critical Rules

### Ownership and Borrowing

- Prefer borrowing (`&T`) over owning (`T`) when you don't need ownership
- Use `Arc<Mutex<T>>` for shared mutable state across threads — never `Rc<RefCell<T>>` in multithreaded code
- Use `Rc<RefCell<T>>` only for graph structures or single-threaded scenarios
- Use `Cow<str>` for functions that may or may not need to allocate
- Use lifetime annotations when the compiler requires them — don't add them unnecessarily
- Prefer `impl Trait` in return position over `Box<dyn Trait>` when possible
- Use `&[T]` for slice parameters — not `&Vec<T>`, not `&[T; N]`

### Error Handling

- Use `Result<T, E>` for all fallible operations — never unwrap in production code
- Use `thiserror` for library error types, `anyhow` for application error types
- Use `?` operator for error propagation — never `.unwrap()` or `.expect()` outside of tests
- Define error enums with `#[derive(thiserror::Error)]` and `#[error("...")]` attributes
- Use `anyhow::Context` to add context: `file.read_to_string(&mut s).context("read config")?`
- Use `Option<T>` for values that may be absent — never `Result<T, ()>`
- Use `ok_or_else` for Option → Result conversion with a computed error

### Type Design

- Use `struct` for data — `enum` for variants — never both in one type
- Use `#[derive(Debug, Clone)]` liberally — add `PartialEq, Eq` when needed
- Use `newtype` wrappers for domain types: `struct UserId(u64);`
- Use `enum` with data for state machines — never multiple `bool` fields
- Implement `From`/`Into` for lossless conversions — never `AsRef` unless the type is generic
- Use `Default` trait for types with sensible defaults

### Project Structure

- One crate per `Cargo.toml` — use workspaces for multi-crate projects
- `src/lib.rs` for library crates, `src/main.rs` for binaries
- `src/bin/` for multiple binaries in one crate
- Use `mod.rs` for module directories — keep module hierarchies shallow
- Put integration tests in `tests/`, benchmarks in `benches/`, examples in `examples/`

### Idiomatic Rust

- Use iterators over `for` loops when transforming data: `.map()`, `.filter()`, `.collect()`
- Use `if let` / `while let` for single-variant matching — `match` for multiple variants
- Use builder pattern for complex constructors: `Thing::builder().x(1).y(2).build()`
- Use `#[cfg(test)] mod tests` for unit tests in the same file
- Use `include_str!` / `include_bytes!` for static assets at compile time
- Use `todo!()` over `unimplemented!()` — both panic, but `todo!()` signals intent
- Use `assert!`, `assert_eq!`, `assert_ne!` in tests — never `panic!` for assertion

### Dependencies

- Keep `Cargo.toml` dependencies minimal — audit with `cargo tree`
- Use feature flags to gate optional functionality: `#[cfg(feature = "json")]`
- Pin dependency versions with `=` only when required for MSRV
- Run `cargo outdated` periodically — update deliberately, not blindly

## Linting / Formatting

```bash
# Format (mandatory)
cargo fmt

# Lint (zero warnings)
cargo clippy -- -D warnings

# Test
cargo test

# Audit dependencies
cargo audit

# Check for outdated
cargo outdated
```

## Anti-Patterns to Avoid

- `.unwrap()` or `.expect()` in non-test code — use `?`, `ok_or`, `unwrap_or_default`
- `unsafe` without a `// SAFETY:` comment
- `clone()` to satisfy the borrow checker — restructure ownership instead
- `String` when `&str` suffices — borrow when you can
- `Vec<T>` when `&[T]` suffices for function parameters
- `Box<dyn Trait>` when `impl Trait` works — use generics over dynamic dispatch
- `Rc<RefCell<T>>` in multithreaded code — use `Arc<Mutex<T>>`
- `println!` in library code — return `Result`, let the caller decide
- `Deref` inheritance pattern — use composition, not `Deref` polymorphism
- Wildcard imports: `use std::collections::*` — name what you use
