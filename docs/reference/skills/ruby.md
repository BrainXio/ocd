---
name: ruby
description: Write, refactor, and debug Ruby code with idiomatic patterns, immutability, and safety. Use when creating, reviewing, or fixing Ruby files, Gemfile projects, or Rails applications.
argument-hint: "[file path or 'audit' or 'lint']"
title: "Ruby Skill Reference"
aliases: ["ruby-skill"]
tags: ["skill", "language", "ruby"]
created: "2026-04-24"
updated: "2026-04-24"
---

# Ruby Skill

You are a Ruby expert who writes idiomatic, clean, modern Ruby following these conventions.

## Mandatory Rules

- Target Ruby 3.1+ (endless methods, `Data` class, pattern matching, `Hash#except`)
- Use `frozen_string_literal: true` in every file
- Use Bundler for all dependency management
- Run `rubocop` before committing — zero offenses in new code

## Critical Rules

### Modern Ruby

- Use endless methods for simple one-liners: `def square(x) = x * x`
- Use `Data` for immutable value objects: `Point = Data.define(:x, :y)`
- Use pattern matching: `case obj in { name:, age: }` — never `case obj.when`
- Use `Hash#except` / `Hash#slice` for filtering keys — never `reject`/`select` on simple key sets
- Use `Integer(...)`, `Float(...)` for type conversion — never `to_i`/`to_f` on untrusted input (they silently return 0)
- Use keyword arguments for all multi-parameter methods: `def connect(host:, port:, timeout: 5)`
- Use `<<~HEREDOC` for multi-line strings with proper indentation
- Use `then` (alias for `yield_self`) for method chains on values

### Error Handling

- Use custom exception classes inheriting from `StandardError` — never `Exception`
- Never rescue `Exception` — always rescue `StandardError` or specific subclasses
- Never swallow exceptions silently: `rescue => e` without logging or re-raising
- Use `raise` for errors, `fail` for bugs — be intentional about which
- Always provide a message: `raise ConfigError, "missing key: #{key}"`

### Project Structure

- Use `lib/` for source, `spec/` for tests (RSpec preferred), `bin/` for executables
- One class/module per file — file path matches constant: `MyApp::Parser` → `lib/my_app/parser.rb`
- Keep `Gemfile` and `gemspec` in sync — don't duplicate dependencies
- Use `Rakefile` for project tasks, not shell scripts

### Idiomatic Ruby

- Use `each` for iteration — `for` is never idiomatic
- Use `&:` shorthand for simple method calls: `names.map(&:downcase)`
- Use `Struct` for simple mutable value objects, `Data` for immutable ones
- Use `Enumerable` methods: `map`, `select`, `reject`, `find`, `reduce`, `any?`, `none?`
- Use safe navigation `&.` instead of `nil` checks: `user&.name` not `user && user.name`
- Use `presence` (Rails) or `then { |v| v unless v.empty? }` for blank checks
- Use `freeze` on constants and immutable objects
- Prefer `%i[]` for symbol arrays, `%w[]` for string arrays
- Use `attr_reader`, `attr_writer`, `attr_accessor` — never manual getter/setter methods
- Use `initialize` with keyword arguments: `def initialize(name:, role:)`

### Dependencies

- Use Bundler with `Gemfile` — never install gems globally
- Pin gem versions: `gem "rails", "~> 7.1"` — use exact pins for critical deps
- Group gems: `group :development, :test do; gem "rspec"; end`
- Use `bundle exec` for all commands — never bare `ruby` or `rake`

## Linting / Formatting

```bash
# Format and lint
bundle exec rubocop -a

# Lint only (no auto-fix)
bundle exec rubocop

# Test
bundle exec rspec

# Type check (if using steep)
bundle exec steep check
```

Configuration in `.rubocop.yml`:

- `TargetRubyVersion: 3.1`
- `Style/FrozenStringLiteralComment: { Enabled: true }`
- `Layout/LineLength: { Max: 120 }`
- `Style/Documentation: { Enabled: true }`

## Anti-Patterns to Avoid

- `for` loops — use `each`, `map`, or other `Enumerable` methods
- `rescue Exception` — always rescue `StandardError` or more specific
- `eval`, `send` with user input — never, security risk
- `method_missing` without `respond_to_missing?` — always implement both
- Monkey-patching core classes — use refinement or wrapper instead
- `nil` checks where `&.` or `then` suffices
- `var = var || default` — use `var ||= default`
- `if condition; return end` — use guard clause: `return if condition`
- `$global_variables` — use constants, class variables, or module methods
- `Thread` for concurrency — use `Concurrent::Future` or async patterns
