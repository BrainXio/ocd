______________________________________________________________________

## name: js description: "Write, refactor, and audit JavaScript with modern syntax, strict equality, and ESLint gates. Use when creating, reviewing, or fixing .js/.mjs/.cjs files, Node.js modules, or browser scripts." argument-hint: "[file path or 'audit' or 'lint']"

# JavaScript Skill

You are a JavaScript expert who writes modern, clean, type-safe JavaScript following these conventions.

## Mandatory Rules

- Target ES2022+ — use `async`/`await`, `const`/`let`, template literals, destructuring, optional chaining
- Always use `===` and `!==` — never `==` or `!=` (loose equality coerces types)
- Always use `const` for declarations — use `let` only when reassignment is needed, never `var`
- Run ESLint with zero warnings — all rules enforced

## Critical Rules

### Syntax and Style

- Use arrow functions for callbacks and short lambdas — use `function` declarations for named exports and methods
- Use template literals for string interpolation — never string concatenation with `+`
- Use destructuring for objects and arrays: `const { name, age } = user` over `user.name`
- Use default parameters: `function greet(name = "World")` over `if (name === undefined)`
- Use spread/rest operators: `...args`, `{...defaults, ...overrides}` over `Object.assign`
- Use optional chaining: `user?.address?.city` over nested `if` checks
- Use nullish coalescing: `const port = config.port ?? 3000` over `||` for defaults (avoids falsy trap)
- Use `for...of` for iterables, `for...in` for object keys — never `for (let i = 0; ...)` for simple iteration
- Use `Array.from()` for array-like objects — never `Array.prototype.slice.call()`

### Modules

- Use ES modules (`import`/`export`) by default — use `require()` only in CommonJS contexts
- Use named exports — avoid default exports (named imports are refactoring-friendly)
- Group exports at the bottom of the file — avoid inline `export` on declarations
- Use `export type` for TypeScript type-only imports when mixing TS and JS
- Use `package.json` `"type": "module"` to enable ESM in Node.js projects
- Use dynamic `import()` for code splitting — never synchronous `require()` in ESM code

### Async and Concurrency

- Use `async`/`await` for all asynchronous operations — never raw `.then()`/`.catch()` chains
- Use `Promise.all()` for concurrent operations — never sequential `await` in a loop when order doesn't matter
- Use `Promise.allSettled()` when you need all results regardless of individual failures
- Use `Promise.race()` for timeouts and fastest-response patterns
- Always handle promise rejections — never let promises float unhandled
- Use `AbortController` for cancellation — never rely on global flags

### Error Handling

- Use custom `Error` subclasses for domain errors: `class ValidationError extends Error {}`
- Always include `cause` when wrapping errors: `throw new AppError("message", { cause: original })`
- Use `try`/`catch` around `await` — never catch with `.catch()` on an awaited promise
- Validate inputs at function boundaries — fail fast with descriptive messages
- Never catch and silently swallow errors — always handle, rethrow, or log

### Collections and Data

- Use `Map` for key-value pairs when keys are not strings — never plain objects as dictionaries
- Use `Set` for unique collections — never arrays with manual deduplication
- Use `Array.prototype.find()` for single lookups — never `filter()[0]`
- Use `Array.prototype.some()` / `Array.prototype.every()` for boolean checks — never `.filter().length > 0`
- Use `Array.prototype.flatMap()` for map-then-flatten — never `.map().flat()`
- Use `Object.entries()` / `Object.keys()` / `Object.values()` for object iteration — never `for...in` with `hasOwnProperty`

### Node.js Specific

- Use `node:` protocol for built-in imports: `import fs from "node:fs"`
- Use `fs/promises` over callback-based `fs` — never use `fs.readFileSync` in production code
- Use `readable` streams for large data — never load entire files into memory
- Use `path.join()` for path construction — never string concatenation
- Use environment variables via `process.env` — never hardcode configuration
- Handle `SIGTERM` and `SIGINT` for graceful shutdown in long-running processes

## Linting / Formatting

```bash
# Lint
eslint .

# Format (if Prettier is configured)
npx prettier --check .

# Type check (if JSDoc types are used)
tsc --noEmit --allowJs --checkJs
```

## Anti-Patterns to Avoid

- `var` — always use `const` or `let`
- `==` and `!=` — always use `===` and `!==`
- Callback hell (nested callbacks) — use `async`/`await`
- `console.log` in production code — use a proper logger
- `new Array()` — use array literals `[]`
- `typeof x === "undefined"` — use optional chaining `x?.` or nullish coalescing `??`
- Modifying function arguments — create new objects/arrays instead
- `instanceof` for primitive checks — use `typeof` for strings, numbers, booleans
- IIFE patterns — use ES modules instead
- `void 0` — use `undefined` directly
- Semicolons omitted inconsistently — pick a style (ASI or explicit) and enforce it project-wide
