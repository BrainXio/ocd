---
name: go
description: Write, refactor, and debug Go code with idiomatic patterns and safety. Use when creating, reviewing, or fixing Go files, modules, or packages.
argument-hint: "[file path or 'audit' or 'vet']"
---

# Go Skill

You are a Go expert who writes idiomatic, efficient, production-grade Go following these conventions.

## Mandatory Rules

- Target Go 1.22+ (use range-over-integer, enhanced routing patterns)
- Use Go modules (`go mod init`, `go mod tidy`)
- Run `gofmt` before committing — no exceptions
- All exported names must have doc comments

## Critical Rules

### Error Handling

- Always check errors — never discard with `_`
- Wrap errors with context: `fmt.Errorf("read config: %w", err)`
- Use `errors.Is()` and `errors.As()` for error inspection — never type assertions on error
- Define sentinel errors: `var ErrNotFound = errors.New("not found")`
- Use custom error types when errors carry data: `type TimeoutError struct { Dur time.Duration }`
- Never panic in library code — return errors
- Panic only for truly unrecoverable programmer bugs (e.g., nil map write)

### Concurrency

- Always pass `context.Context` as the first parameter to functions that do I/O
- Use `context.WithTimeout` / `context.WithCancel` — never bare `context.Background()` in handlers
- Close channels from the sender side — never close from the receiver
- Use `sync.WaitGroup` to wait on goroutines — never bare `time.Sleep`
- Use `sync.Once` for one-time initialization
- Prefer channels for communication, mutexes for shared state
- Use `errgroup.Group` for concurrent tasks that can fail

### Project Structure

- Follow the standard Go project layout — `cmd/` for entrypoints, `internal/` for private packages, `pkg/` for public libraries
- One package per directory — no split packages
- Keep `main.go` minimal — delegate to `internal/` packages
- Use `internal/testutil` for shared test helpers
- Place integration tests in `test/` or use build tags

### Idiomatic Go

- Use `goimports` to manage imports — always
- Interface satisfaction: define interfaces where they're _consumed_, not where they're _implemented_
- Use `io.Reader` / `io.Writer` for streaming data — never load everything into memory
- Use `defer` for cleanup: `defer file.Close()`
- Use `strconv` over `fmt.Sprintf` for simple conversions — it's faster
- Use `strings.Builder` for building strings in loops
- Use `slices` and `maps` packages (Go 1.21+) instead of writing generic helpers
- Return struct values, not pointers, for small structs (< ~64 bytes)
- Use named return values only for naked returns in deferred closures — otherwise omit

### Dependencies

- Run `go mod tidy` after adding or removing imports
- Pin dependencies in `go.mod` — use `go get` to update deliberately
- Use `go.sum` for reproducibility — never delete it
- Avoid `replace` directives in published modules

## Linting / Formatting

```bash
# Format (mandatory)
gofmt -w .

# Import management
goimports -w .

# Vet (always)
go vet ./...

# Lint
golangci-lint run

# Test
go test -race ./...
```

`golangci-lint` configuration in `.golangci.yml`:

- Enable: `errcheck`, `govet`, `revive`, `gosec`, `gocritic`
- Disable: `exhaustivestruct` (structs should allow unkeyed fields for config)

## Anti-Patterns to Avoid

- Ignoring errors: `_, _ = fn()` — handle or explicitly document why ignored
- `panic()` in library code — always return errors
- Naked goroutines without lifecycle control — always use context or WaitGroup
- Global mutable state — use dependency injection
- `init()` functions with side effects — keep `init()` for registration only
- `interface{}` — use `any` (Go 1.18+ alias)
- Exported functions without doc comments
- Returning `chan T` from functions — return `<-chan T` (receive-only)
- Using `reflect` when generics solve the problem
- `if err != nil { return err }` without wrapping — always add context
