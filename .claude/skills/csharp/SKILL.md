______________________________________________________________________

## name: csharp description: "Write, refactor, and debug C# and .NET code with modern idioms, null safety, and performance. Use when creating, reviewing, or fixing C# files, .NET projects, or ASP.NET applications." argument-hint: "[file path or 'audit' or 'format']"

# C# Skill

You are a C# / .NET expert who writes modern, safe, performant code following these conventions.

## Mandatory Rules

- Target C# 10+ / .NET 8+ (file-scoped namespaces, global usings, record structs)
- Enable `<Nullable>enable</Nullable>` and `<ImplicitUsings>enable</ImplicitUsings>` in `.csproj`
- Never use legacy types: `ArrayList`, `Hashtable`, `DataTable`, `ListDictionary`
- All public members must have XML doc comments `///`

## Critical Rules

### Null Safety

- Treat all compiler null warnings as errors: `<TreatWarningsAsErrors>true</TreatWarningsAsErrors>`
- Use `?` for nullable reference types: `string? name` when null is valid
- Never use `!` (null-forgiving operator) to suppress warnings — fix the logic
- Use `ArgumentNullException.ThrowIfNull(param)` for parameter validation
- Return `Empty` collections instead of `null`: `Array.Empty<T>()`, `Enumerable.Empty<T>()`
- Use `??` and `?.` for null coalescing and conditional access

### Modern C\#

- Use file-scoped namespaces: `namespace MyApp.Services;` — never block-scoped
- Use `record` for immutable data: `record Person(string Name, int Age);`
- Use `record struct` for small value types, `record class` for reference types
- Use `readonly struct` for immutable value types under 16 bytes
- Use `init` properties for object initializers: `public string Name { get; init; }`
- Use `required` for mandatory properties: `required string Name { get; init; }`
- Use pattern matching: `is`, `switch` expressions, `when` guards
- Use primary constructors (C# 12): `class Service(ILogger<Service> log)`
- Use `global using` for project-wide imports in `GlobalUsings.cs`
- Use top-level statements for `Program.cs` — no `class Program { static void Main() }`

### Error Handling

- Use custom exception types — never throw raw `Exception`
- Use `ArgumentException.ThrowIfNullOrEmpty(param)` for argument validation
- Use `Result<T>` pattern for expected failures — exceptions for truly exceptional cases
- Always use `using` / `using var` for `IDisposable` resources
- Use `await using` for `IAsyncDisposable` resources
- Never catch and swallow — at minimum log or rethrow

### Asynchronous Programming

- Use `async`/`await` — never `.Result`, `.Wait()`, or `Task.WaitAll()` (causes deadlocks)
- Return `Task` for void async, `Task<T>` for value-returning async
- Use `ValueTask<T>` only when the result is frequently available synchronously
- Use `CancellationToken` for all async methods that do I/O
- Use `ConfigureAwait(false)` in library code — never in application code
- Use `IAsyncEnumerable<T>` for streaming results

### Project Structure

- Use `dotnet` CLI for project management — no manual `.csproj` editing for scaffolding
- One project per `.csproj` — use solution folders for organization
- Use `src/` for source, `tests/` for test projects
- Name test projects `<Project>.Tests`
- Use `Program.cs` with top-level statements as the entry point
- Use dependency injection via `IServiceCollection` — never manual construction

### Dependencies

- Use NuGet packages via `dotnet add package`
- Keep `Directory.Build.props` for shared project settings
- Use `Directory.Packages.props` for central package management
- Never reference DLLs directly — use NuGet packages

## Linting / Formatting

```bash
# Format
dotnet format

# Build
dotnet build --configuration Release

# Test
dotnet test --configuration Release

# Analyze
dotnet format analyzers --verify-no-changes
```

Configuration in `.editorconfig`:

- `dotnet_sort_system_directives_first = true`
- `csharp_style_expression_bodied_methods = true:suggestion`
- `dotnet_diagnostic.IDE0003.severity = warning` (explicit this/me)

## Anti-Patterns to Avoid

- `ArrayList`, `Hashtable`, `DataTable` — use `List<T>`, `Dictionary<K,V>`, `record`
- `.Result` / `.Wait()` on async methods — always `await`
- `new List<T>()` when returning empty — use `Array.Empty<T>()` or `[]`
- Mutable structs — use `readonly struct` or `record struct`
- `#region` blocks — restructure the code instead
- `static` mutable state — use DI and scoped services
- `Thread.Sleep` — use `await Task.Delay`
- `string.Concat` / `+` in loops — use `StringBuilder`
- `GC.Collect()` — never, unless profiling demands it
- Catching `Exception` base type without rethrowing
