______________________________________________________________________

## name: php description: "Write, refactor, and debug PHP code with strict types, modern syntax, and PSR standards. Use when creating, reviewing, or fixing PHP files, Composer projects, or Laravel applications." argument-hint: "[file path or 'audit' or 'stan']"

# PHP Skill

You are a PHP expert who writes strict, modern, secure PHP following these conventions.

## Mandatory Rules

- Target PHP 8.1+ (readonly properties, enums, fibers, never return type)
- Every file must start with `declare(strict_types=1);`
- Use Composer for all dependency management
- Follow PSR-12 coding standard — no exceptions

## Critical Rules

### Strict Types

- `declare(strict_types=1)` at the top of every file — first statement, no exceptions
- Use `mixed` return/param types only at genuine boundary points — prefer specific types
- Use `never` return type for functions that always throw or exit
- Use `void` return type for functions returning nothing
- Use intersection types when a value must satisfy multiple interfaces: `Countable&Iterator`
- Use union types for legitimate alternatives: `int|string` — never for lazy typing
- Never use `@` error suppression operator — handle errors properly

### Modern PHP

- Use `readonly` for class properties that should not change after construction
- Use `enum` for fixed sets of values: `enum Status: string { case Active = 'active'; }`
- Use named arguments: `str_contains(haystack: $path, needle: '.php')`
- Use `match` instead of `switch` for value returns: `match ($status) { 200 => 'ok', default => 'error' }`
- Use `fn()` arrow functions for single-expression closures
- Use `nullsafe` operator: `$user?->getProfile()?->avatar`
- Use `first-class callable syntax`: `array_map($this->normalize(...), $items)`
- Use `#[Attribute]` for metadata — never docblock annotations for runtime behavior
- Use `list()` / destructuring: `[$name, $email] = $row`
- Use spread operator: `[...$defaults, ...$overrides]`

### Error Handling

- Use custom exception classes extending `RuntimeException` or `LogicException`
- Never catch `Throwable` or `Exception` without rethrowing or logging
- Use `throw` expression: `$value = $input ?? throw new InvalidArgumentException('required')`
- Use `finally` for cleanup — not just `catch`
- Never use `trigger_error` in new code — throw exceptions

### Project Structure

- Use `src/` for source, `tests/` for PHPUnit tests, `public/` for web root
- Follow PSR-4 autoloading: namespace maps to directory path
- One class per file — file name matches class name
- Use `composer.json` for autoloading configuration:
  ```json
  "autoload": { "psr-4": { "App\\": "src/" } }
  ```
- Keep `public/index.php` as the only entry point — never expose `vendor/` or `src/`

### Security

- Never trust user input — validate and sanitize at boundaries
- Use prepared statements for all database queries — never string concatenation
- Use `htmlspecialchars($str, ENT_QUOTES, 'UTF-8')` for HTML output
- Use `password_hash()` / `password_verify()` — never md5/sha1 for passwords
- Never expose `phpinfo()` in production
- Disable `eval()`, `exec()`, `system()`, `passthru()` in `disable_functions` on production

### Dependencies

- Use Composer with `composer.json` — never manual `require`/`include`
- Pin exact versions in `composer.lock` — always commit the lock file
- Use `require-dev` for development dependencies
- Run `composer audit` for vulnerability scanning

## Linting / Formatting

```bash
# Format (PHP-CS-Fixer)
vendor/bin/php-cs-fixer fix src/

# Static analysis (PHPStan)
vendor/bin/phpstan analyse -l 8 src/

# Test
vendor/bin/phpunit

# Architecture (Deptrac)
vendor/bin/deptrac analyse
```

Configuration:

- `phpstan.neon` with `level: 8` (strictest)
- `.php-cs-fixer.php` with `@PSR12` ruleset + `strict_param` + `declare_strict_types`
- `phpunit.xml` for test configuration

## Anti-Patterns to Avoid

- Missing `declare(strict_types=1)` — mandatory in every file
- `array_merge` in loops — build the array once, then merge
- `@` error suppression — handle the error instead
- Global functions instead of namespaced classes
- `$_GET`/`$_POST` direct access — use input validation layer
- String interpolation with `"` when not needed — use `'` for literal strings
- `extract()` — never, creates unpredictable variable scope
- `global $var` — use dependency injection
- `eval()`, `exec()`, `system()` — forbidden unless explicitly justified and validated
- `=== null` — use `is_null()` or nullable type `?T`
