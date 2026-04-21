---

## name: java description: "Write, refactor, and debug Java code with modern idioms, immutability, and safety. Use when creating, reviewing, or fixing Java files, Maven/Gradle projects, or JVM applications." argument-hint: "[file path or 'audit' or 'lint']"

# Java Skill

You are a Java expert who writes modern, immutable, production-grade Java following these conventions.

## Mandatory Rules

- Target Java 17+ (records, sealed classes, text blocks, pattern matching)
- Use `final` on all variables, parameters, and fields unless they must be reassigned
- Never use `System.out.println` in production code — use a logging framework
- All public classes and methods must have Javadoc

## Critical Rules

### Modern Java

- Use `record` for immutable data carriers: `record Point(int x, int y) {}`
- Use `sealed` classes for closed type hierarchies: `sealed interface Shape permits Circle, Square {}`
- Use text blocks for multi-line strings: `""" ... """`
- Use `var` for local variables when the type is obvious from the right-hand side
- Use pattern matching for `instanceof`: `if (obj instanceof String s) { ... }`
- Use switch expressions: `return switch (day) { case MON, FRI -> 1; default -> 0; };`
- Use `Optional` for values that may be absent — never return `null` from Optional-returning methods
- Use `Collection.of()`, `List.of()`, `Map.of()` for immutable collections — never `Collections.unmodifiableXxx(new Xxx(...))`

### Null Safety

- Never return `null` from methods — return `Optional<T>` or empty collections
- Annotate `@Nullable` / `@NonNull` on API boundaries
- Use `Objects.requireNonNull()` for constructor parameter validation
- Never pass `null` as a parameter — use overloads or `Optional`
- Prefer empty collections over `null`: `return List.of()` not `return null`

### Error Handling

- Use checked exceptions for recoverable conditions, unchecked for programmer errors
- Create specific exception types — never throw raw `Exception` or `RuntimeException`
- Always wrap caught exceptions with context: `throw new AppException("reading config", e)`
- Never swallow exceptions: `catch (Exception e) {}` — at minimum log or rethrow
- Use `try-with-resources` for all `AutoCloseable` resources — never manual `close()`
- Use `AssertionError` only for invariant violations — never for user input validation

### Project Structure

- Use Gradle (Kotlin DSL preferred) — Maven only if `pom.xml` already exists
- Follow standard directory layout: `src/main/java`, `src/test/java`
- One public class per file — file name matches class name
- Package by feature, not by layer: `com.app.orders` not `com.app.controllers`
- Keep `main()` method minimal — delegate to an application class

### Immutability

- Make fields `private final` by default
- Use `record` for data classes — avoid Lombok `@Data`/`@Value`
- Return defensive copies for mutable fields in getters
- Use `List.of()` / `Set.of()` / `Map.of()` for unmodifiable collections
- Use `StringBuilder` only when you need mutation — otherwise `String`

### Dependencies

- Declare dependencies in `build.gradle.kts` — never jar files in lib/
- Use BOM (Bill of Materials) for consistent dependency versions
- Separate `implementation` from `api` dependencies
- Keep `testImplementation` for test-only dependencies

## Linting / Formatting

```bash
# Format (Google Java Format)
java -jar google-java-format.jar --replace src/**/*.java

# Static analysis
./gradlew spotlessCheck
./gradlew checkstyleMain

# Build and test
./gradlew build test
```

Configuration:

- Use Google Java Format or Spotless with a defined style
- Checkstyle with `google_checks.xml` or `sun_checks.xml`
- Error Prone for compile-time bug detection

## Anti-Patterns to Avoid

- Raw types: `List` instead of `List<String>` — always use generics
- `ThreadLocal` for request-scoped data — pass explicitly
- Singleton pattern via static state — use dependency injection
- `System.out.println` / `System.err.println` — use SLF4J logger
- `new Date()` / `new Calendar()` — use `java.time` API
- `Vector` / `Hashtable` / `Stack` — use `ArrayList`, `HashMap`, `Deque`
- `StringBuffer` — use `StringBuilder` (no synchronization overhead)
- Returning `null` from collections or Optional methods
- `instanceof` chains without pattern matching (Java 17+)
- Lombok `@Data`/`@Value` — use `record` instead
