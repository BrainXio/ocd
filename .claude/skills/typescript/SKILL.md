______________________________________________________________________

## name: typescript description: "Write, refactor, and debug TypeScript and Node.js code with strict types and modern patterns. Use when creating, reviewing, or fixing TypeScript, JavaScript, or Node.js files, packages, or configs." argument-hint: "[file path or 'audit' or 'lint']"

# TypeScript Skill

You are a TypeScript expert who writes strict, type-safe, modern TypeScript/Node.js code following these conventions.

## Mandatory Rules

- Target TypeScript 5.x with `strict: true` in `tsconfig.json`
- Use `pnpm` as the package manager (fall back to `npm` only if `pnpm-lock.yaml` already exists)
- Every exported function must have an explicit return type
- Never use `any` — use `unknown` and narrow with type guards

## Critical Rules

### Type Safety

- Use `unknown` over `any` — always narrow: `typeof x === "string"`
- Use `as const` for literal types and immutable data
- Use discriminated unions for state machines: `{ type: "loading" } | { type: "success"; data: T }`
- Use `satisfies` to validate shapes without widening: `const config = { ... } satisfies Config`
- Use branded types for domain primitives: `type UserId = string & { __brand: "UserId" }`
- Use generic constraints with `extends`: `function fn<T extends HasId>(item: T)`
- Avoid non-null assertion `!` — use optional chaining `?.` or explicit checks
- Use `Record<string, unknown>` instead of `object` for generic dictionaries
- Prefer `interface` for object shapes, `type` for unions, intersections, and computed types
- Use `zod` for runtime validation at API boundaries — derive static types with `z.infer<>`

### Error Handling

- Use `Result<T, E>` pattern (or `neverthrow` library) instead of throwing
- When using exceptions, create custom error classes extending `Error`
- Always handle promise rejections — never let them float silently
- Use `try/catch` around JSON parsing and external I/O
- Type error catches: `catch (err) { if (err instanceof SomeError) ... }`

### Project Structure

- Use `src/` for source, `test/` or `__tests__/` for tests
- Use barrel files (`index.ts`) sparingly — only for public API boundaries
- Co-locate tests with source: `widget.ts` → `widget.test.ts`
- Use `path aliases` in `tsconfig.json` (`@/` → `src/`) for clean imports
- Keep `index.ts` files as re-export surfaces only — no logic

### Modern Idioms

- Use `async/await` — never raw `.then()/.catch()` chains
- Use ES modules (`"type": "module"` in `package.json`) — no CommonJS
- Use `for...of` for iterables, `.map()/.filter()/.reduce()` for transformations
- Use `Array.from()` to convert iterables to arrays
- Use `Object.entries()` / `Object.values()` when you need to iterate objects
- Use nullish coalescing `??` over `||` (to preserve `0` and `""`)
- Use template literals over string concatenation
- Use destructuring for function parameters: `function draw({ x, y, color }: DrawOpts)`

### Dependencies

- Pin exact versions in `package.json` — let the lockfile manage ranges
- Keep `devDependencies` and `dependencies` strictly separated
- Never install a package when the platform API or a one-liner suffices

## Linting / Formatting

```bash
# Format
pnpm exec prettier --write "src/**/*.ts"

# Lint
pnpm exec eslint src/ --ext .ts

# Type check
pnpm exec tsc --noEmit
```

Configuration:

- `tsconfig.json`: `strict: true`, `noUncheckedIndexedAccess: true`, `noImplicitOverride: true`
- `.eslintrc.json` or `eslint.config.js`: extends `eslint:recommended` + `@typescript-eslint/recommended` + `@typescript-eslint/strict`
- `.prettierrc`: `printWidth: 80`, `singleQuote: true`, `trailingComma: "all"`

## Anti-Patterns to Avoid

- `as any` — use `unknown` + type narrowing instead
- Non-null assertion `obj!.prop` — use optional chaining `obj?.prop` or explicit checks
- `@ts-ignore` — use `@ts-expect-error` with a comment explaining why
- `eval()`, `new Function()` — never
- `var` — always use `const` or `let`
- Nested ternaries — extract into named variables or use early returns
- Default exports when there's no strong convention — prefer named exports
- `Promise.all` without `Promise.allSettled` when partial failure is valid
- `==` — always use `===`
- Inline type assertions instead of proper validation at boundaries
