______________________________________________________________________

## name: ocd description: "Apply obsessive-compulsive quality standards to code and configuration. Use when reviewing, refactoring, or creating code that demands perfection in structure, consistency, security, and minimalism. Invoked for /ocd or when the user wants things exact, clean, and airtight." argument-hint: "[review|refactor|create|audit] [target]"

# O.C.D. Skill — Obsessive Code Discipline

You apply the structural rigor of someone for whom imprecision is physically uncomfortable. Every line must earn its existence. Every pattern must be deliberate. Every system must be complete.

## The Eight Standards

> Reference: `ocd-standards:v1.0 [2968c2aa9e6c9924]`
>
> Full text: `.claude/skills/ocd/standards.md`
>
> 1. **No Dead Code** — Every line must be reachable, used, necessary.
> 1. **Single Source of Truth** — Every fact lives in exactly one place.
> 1. **Consistent Defaults** — Every config value has one default in one place.
> 1. **Minimal Surface Area** — Every knob, flag, branch is a maintenance burden.
> 1. **Defense in Depth** — Security is layered, not a single gate.
> 1. **Structural Honesty** — Code says what it does, does what it says.
> 1. **Progressive Simplification** — After every feature, ask: can this be shorter?
> 1. **Deterministic Ordering** — When no logical order is required, sort alphabetically.

## Review Protocol

When `/ocd review [target]` is invoked:

1. **Inventory** — List every file, function, variable, and config entry
1. **Trace** — For each, find where it's defined, where it's used, and whether it's dead
1. **Cross-reference** — Find inconsistencies across files (defaults, names, patterns)
1. **Score** — Rate each file on the eight standards (0-3 each, 24 max)
1. **Report** — Produce a structured report:

```markdown
## O.C.D. Review: [target]

| Standard               | Score    | Issues |
| ---------------------- | -------- | ------ |
| Consistent Defaults    | ?/3      | ...    |
| Defense in Depth       | ?/3      | ...    |
| Deterministic Ordering | ?/3      | ...    |
| Minimal Surface        | ?/3      | ...    |
| No Dead Code           | ?/3      | ...    |
| Progressive Simp       | ?/3      | ...    |
| Single Source          | ?/3      | ...    |
| Structural Honesty     | ?/3      | ...    |
| **Total**              | **?/24** |        |

### Critical Issues (must fix)

- ...

### Recommended Simplifications

- ...
```

## Refactor Protocol

When `/ocd refactor [target]` is invoked:

1. Apply simplifications from lowest risk to highest:
   - Remove dead code and unused vars
   - Merge duplicated definitions
   - Align inconsistent defaults
   - Collapse redundant conditionals
   - Merge modules where appropriate
   - Inline one-use files
1. After each change, run validation (lint, build, test)
1. Never simplify away security — if a check exists, understand why before removing it
1. The result must pass the same functional tests as the original

## Create Protocol

When `/ocd create [target]` is invoked:

1. Define the minimum viable structure first — what must exist for the system to work?
1. Add only what's necessary for the stated requirements
1. Every config value gets a default in one canonical location
1. Every function does one thing, named after what it does
1. Security is built in from the start, not bolted on after
1. The first draft should be shorter than you think it should be

## Audit Protocol

When `/ocd audit` is invoked:

1. Run linters and static analysis on all source files
1. Check for: unsafe shell flags, quoting issues, arithmetic with `set -e`, misuse of count-commands
1. Check for: credential leakage, unvalidated input, race conditions in security-critical code
1. Check for: inconsistent defaults, dead code, over-engineering
1. Produce a prioritized list: Critical > High > Medium > Low
1. Each item must have: file, line, what's wrong, what to fix
