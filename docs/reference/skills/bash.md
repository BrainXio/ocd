---
name: bash
description: Write, audit, and debug shell scripts with strict safety practices. Use when creating, reviewing, or fixing bash scripts, shell functions, or CI pipeline steps.
argument-hint: "[script path or 'audit' or 'debug']"
title: "Bash Skill Reference"
aliases: ["bash-skill"]
tags: ["skill", "language", "bash"]
created: "2026-04-24"
updated: "2026-04-24"
---

# Bash Skill

You are a shell scripting expert who writes robust, production-grade bash following these strict conventions.

## Mandatory Script Header

Every script must start with:

```bash
#!/bin/bash
set -euo pipefail
```

Never use `#!/bin/sh` unless POSIX compatibility is explicitly required. Always use `set -euo pipefail` — no exceptions.

## Critical Rules

### Error Handling

- `set -e`: Exit on any command failure. Never suppress with `|| true` unless the command is genuinely expected to fail
- `set -u`: Treat unset variables as errors. Always use `${VAR:-default}` for optional variables
- `set -o pipefail`: Pipeline fails if any command in it fails
- Never use `((var--))` with `set -e` — use `var=$((var - 1))` instead
- Always handle command failures explicitly: check exit codes, use `if` guards, or provide fallbacks

### Variable Safety

- Quote all variable expansions: `"$var"`, `"${var}"`, never bare `$var`
- Use `${VAR:-default}` for all env vars and optional parameters
- Use `local` for function-scoped variables
- Use `declare -A` for associative arrays, `declare -a` for indexed arrays
- Never use uppercase variable names for local variables (reserved for env vars)

### Functions

- Always use the `function_name() { ... }` syntax
- Always declare local variables inside functions
- Return meaningful exit codes: `0` for success, `1` for failure
- Use `log()` or `error()` helper functions for consistent output with prefixes like `[SCRIPT_NAME]`

### Subshells and Pipelines

- Be aware that `while read` in a pipeline runs in a subshell — variables set inside are lost
- Use process substitution `< <(command)` or temporary files when you need to preserve state
- Use `mapfile -t arr < <(command)` to capture command output into arrays

### Security

- Never pipe unverified remote content into `sh` or `bash`
- Validate all user input and environment variables before use
- Use `[[ ]]` for conditional tests (not `[ ]` or `test`)
- Validate CIDR notation, IPs, and URLs with proper regex patterns
- Never store credentials in shell scripts; use env files with restricted permissions (`chmod 600`)
- Always use `rm -f` (not bare `rm`) for cleanup of known paths

### Idempotency

- Always check before appending to config files: `if ! grep -q 'pattern' file; then echo '...' >> file; fi`
- Use `mkdir -p` instead of `mkdir` (creates parent dirs, doesn't fail if exists)
- Use `2>/dev/null || true` for commands that may fail harmlessly

## Script Structure

```bash
#!/bin/bash
set -euo pipefail

log() { echo "[MYSCRIPT] $*"; }
error() { echo "[MYSCRIPT] ERROR: $*" >&2; }

configure() {
    # Function body
}

validate() {
    # Check that setup worked
}

# Main
configure
validate
log "Done"
```

## Linting

Always run `shellcheck` on scripts before committing:

```bash
shellcheck --severity=warning scripts/*.bash
```

Common shellcheck suppressions to use sparingly:

- `SC2086`: Double quote to prevent globbing (use `# shellcheck disable=SC2086` when intentionally word-splitting)
- `SC2016`: Single quotes prevent expansion (use when expressing variable names literally)

## Debugging Patterns

- Use `bash -x script.sh` to trace execution
- Use `set -x` / `set +x` around specific sections for targeted debugging
- Log function entry/exit with: `log "Entering ${FUNCNAME[0]}"` / `log "Exiting ${FUNCNAME[0]}"`
- For complex conditionals, extract into named functions for readability
- Use `trap 'error "Line $LINENO"' ERR` for line-number error reporting in development

## Anti-Patterns to Avoid

- `for i in $(cat file)` — use `mapfile` or `while IFS= read -r line`
- `echo "$var" | grep pattern` — use `[[ $var =~ pattern ]]` instead
- `ls | grep` — use `find` or `ls` with globs
- `cat file | command` — use `command < file` instead
- `expr` for arithmetic — use `$(( ))` instead
- `which` for checking commands — use `command -v` instead
- `sed -i` on files you don't control — use a temp file pattern
