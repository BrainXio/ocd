---
version: "1.0"
hash: 2968c2aa9e6c9924
---

### 1. No Dead Code

Every line must be reachable, used, and necessary. If a function is never
called, delete it. If a variable is set but never read, remove it. If a flag is
defined but defaults to a value that makes it inert, eliminate it. Code that
exists "just in case" is code that rots.

**Check:** Search for every function name. If it appears only in its definition,
it's dead. Search for every config variable. If it's set but never read at
runtime, it's dead.

### 2. Single Source of Truth

Every fact lives in exactly one place. If a connection string appears in three
config files, it's defined in three places. Extract it to one canonical source
and reference it everywhere else. If a list of values appears in two scripts,
it's defined in two places — merge into one lookup table.

**Check:** Search the same string across all files. If it appears more than once
in a non-trivial way, it should be a variable or a shared definition.

### 3. Consistent Defaults

Every configuration value has exactly one default, stated in exactly one place.
If a variable defaults to `false` in the environment but `true` in the config
file, that's an inconsistency bug waiting to happen. One location is the source
of truth. All other locations either override it or don't set it at all.

**Check:** For each config variable, find its default in every file where it
appears. All defaults must match or have an explicit comment explaining the
difference.

### 4. Minimal Surface Area

Every configuration knob, every flag, every conditional branch is a maintenance
burden. Before adding a new option, ask: can the system derive this from
context? Can the user achieve the same result with an existing mechanism? Can we
remove three flags by replacing them with one list?

**Check:** Count config variables. If any default to `false` and nobody enables
them, remove them. If any have identical behavior in both branches of an
if/else, collapse the branch. If two flags control overlapping domains, merge
them.

### 5. Defense in Depth

Security is not a single gate — it's layered. If there's a firewall, the
applications behind it should also validate. If there's input validation, the
database should also constrain. Every trust boundary gets its own check. And
every security check must be correct: a check that counts lines instead of
values is a bug, not a feature.

**Check:** For every boundary (network, file, API), ask: what happens if this
is bypassed? What's the second line of defense? Are validation checks actually
validating, or just checking that something exists?

### 6. Structural Honesty

Code should say what it does and do what it says. A function called
`apply_rules` should apply rules — not also resolve DNS, fetch remote resources,
and validate the result. A variable called `ALLOWED_DOMAINS` should contain
allowed domains — not sometimes be empty and sometimes be overwritten. A comment
saying "always block telemetry" should correspond to code that always blocks
telemetry, not code gated by a flag.

**Check:** Read each function name. Read its body. Does the name match the
behavior? Read each variable name. Read its assignments. Does the name match
the values? Read each comment. Does it match the code below it?

### 7. Progressive Simplification

After every feature is complete, ask: can this be shorter without losing
meaning? Can these three functions become one? Can this 30-line conditional
become a 10-line lookup table? Can this entire file be inlined into the one
place it's used? The target is not minimal for minimal's sake — it's minimal
because every unnecessary line is a line that can go wrong.

**Check:** For each file, compare line count to functional scope. If a file is
twice as long as it needs to be to fulfill its purpose, the excess is debt.

### 8. Deterministic Ordering

When no logical sequence is required for correctness or clarity, sort
alphabetically. Tables, lists, imports, enums, and switch cases all get this
treatment. When a logical sequence is required (e.g., execution steps,
dependency chains), use that — but document why alphabetical isn't sufficient.
Random or insertion-order grouping hides patterns and makes things harder to
find.

**Check:** For every list, table, or ordered collection, ask: is this in a
defined order? If not, sort it alphabetically. If the order is intentional but
non-obvious, add a comment explaining why.
