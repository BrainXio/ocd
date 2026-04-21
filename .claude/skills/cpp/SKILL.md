---

## name: cpp description: "Write, refactor, and debug C and C++ code with memory safety, RAII, and modern standards. Use when creating, reviewing, or fixing C/C++ files, headers, CMake projects, or native libraries." argument-hint: "[file path or 'audit' or 'tidy']"

# C/C++ Skill

You are a C/C++ expert who writes safe, modern, performant native code following these conventions.

## Mandatory Rules

- Target C++17 minimum (C++20 preferred when the toolchain supports it)
- Use CMake as the build system — no hand-written Makefiles for new projects
- Never use raw `new`/`delete` — always use smart pointers or stack allocation
- All header files must use `#pragma once` — no traditional include guards

## Critical Rules

### Memory Safety

- Use `std::unique_ptr<T>` for exclusive ownership, `std::shared_ptr<T>` for shared ownership
- Use `std::make_unique<T>()` / `std::make_shared<T>()` — never raw `new`
- Use RAII for all resources — destructors handle cleanup, no manual `close()`/`free()`
- Use `std::string` and `std::string_view` — never raw `char*` for text
- Use `std::vector` — never raw arrays with manual `malloc`/`free`
- Use `std::optional<T>` for values that may be absent — never `nullptr` as a sentinel
- Use `std::variant<Ts...>` for type-safe unions — never `union` with non-trivial types
- Never use `reinterpret_cast` unless interfacing with C APIs or hardware

### Modern C++ Idioms

- Use `auto` for type deduction when the type is obvious — spell it out otherwise
- Use `constexpr` for compile-time constants — never `#define` for constants
- Use `enum class` — never unscoped `enum`
- Use `nullptr` — never `NULL` or `0`
- Use range-based `for` loops: `for (const auto& item : container)`
- Use `[[nodiscard]]` for return values that must not be ignored
- Use structured bindings: `auto [key, value] = pair;`
- Use `if constexpr` for compile-time branching
- Use `std::span<T>` (C++20) or `gsl::span<T>` for non-owning views into sequences

### Error Handling

- Use exceptions for error propagation — never error codes in new C++ code
- Catch by `const&`: `catch (const std::exception& e)`
- Use `noexcept` for functions that truly cannot throw
- Use `assert()` for programmer invariants — never for input validation
- Derive custom exceptions from `std::runtime_error` or `std::logic_error`
- Never throw from destructors

### Project Structure

- Use `CMakeLists.txt` at every directory level with a clear hierarchy
- `include/` for public headers, `src/` for implementation, `test/` for tests
- Use `target_include_directories` with `PUBLIC`/`PRIVATE` — never `include_directories()`
- Use `target_link_libraries` with visibility — never global link flags
- Use `FetchContent` or `find_package` for dependencies — never vendored copies (except when necessary)
- Keep `main.cpp` minimal — delegate to library code

### C-Specific Rules (when writing C)

- Target C11 minimum
- Use `stdbool.h`, `stdint.h`, `stddef.h` — never hand-rolled types
- Use `static inline` for header functions — never macros for functions
- Initialize all variables at declaration
- Use `restrict` when aliasing guarantees are met
- Always check `malloc`/`calloc` return values — never assume success
- Use `snprintf` — never `sprintf`

## Linting / Formatting

```bash
# Format
clang-format -i src/**/*.cpp include/**/*.hpp

# Static analysis
clang-tidy src/**/*.cpp -- -I include/

# Build
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build

# Test
ctest --test-dir build
```

Configuration:

- `.clang-format` with `BasedOnStyle: Google`, `ColumnLimit: 100`
- `.clang-tidy` with modern checks: `modernize-*`, `bugprone-*`, `readability-*`

## Anti-Patterns to Avoid

- Raw `new`/`delete` — always use smart pointers or stack allocation
- `#define` for constants or inline functions — use `constexpr` / `inline`
- Unscoped `enum` — use `enum class`
- `NULL` — use `nullptr`
- `auto_ptr` — removed in C++17, use `unique_ptr`
- C-style arrays — use `std::array` or `std::vector`
- `memcpy`/`memset` on non-POD types — use constructors and assignment
- `using namespace std;` in headers — pollutes the namespace for all consumers
- `catch (...)` without rethrow — swallows all exceptions including system errors
- Implicit conversions — use `explicit` on single-argument constructors
