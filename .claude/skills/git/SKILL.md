______________________________________________________________________

## name: git description: "Conventional git workflow: commits, branches, rebases, and hygiene. Use when the user asks to commit, branch, merge, rebase, squash, or manage git history. Invoked for /git or when the user wants version control operations." argument-hint: "[commit|branch|rebase|squash|merge|log|diff|status|fixup] [args]"

# Git Skill

You follow Conventional Commits and a clean branching strategy. Every commit tells a story. Every branch has a purpose. History is linear where possible.

## Conventional Commits

All commit messages follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**

- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code restructuring without behavior change
- `docs`: Documentation only
- `style`: Formatting, whitespace, semicolons (no logic change)
- `test`: Adding or updating tests
- `ci`: CI/CD configuration
- `chore`: Build process, tooling, dependencies
- `perf`: Performance improvement
- `revert`: Reverting a previous commit

**Rules:**

- Subject line: lowercase, imperative mood, no period, under 72 characters
- Body: explain *why*, not *what* — the diff shows what
- No Co-Authored-By lines, no AI attribution tags
- No emoji prefixes (the type prefix is the signal)
- One logical change per commit — if you fixed a bug and refactored a function, that's two commits

**Examples:**

```
feat(auth): add token refresh on expiry

fix(parser): handle empty input in decode loop

refactor(config): extract defaults into single source

docs(readme): document required environment variables
```

## Branching Strategy

```
main          ────●────●────●────●────
                  \              /
feat/token-refresh   ●───●───●───╱
```

**Branch naming:**

- `feat/<short-description>` — new features
- `fix/<short-description>` — bug fixes
- `refactor/<short-description>` — restructuring
- `docs/<short-description>` — documentation
- `chore/<short-description>` — tooling, CI, dependencies

**Rules:**

- Branch from `main` for every change — no long-lived branches
- Rebase onto `main` before merging to keep history linear
- Merge via `gh pr merge --squash --delete-branch` — branch protection prevents
  direct push to main; configure GPG in GitHub for signed squash merges
- Delete branches after merge

## Commands

### `/git commit [message]`

1. Run `git status` and `git diff --staged` to understand what's changing
1. Stage specific files with `git add` — never `git add -A` or `git add .`
1. If the user provided a message, use it as the subject (convert to conventional format if needed)
1. If no message, infer the type and scope from the diff and write a conventional commit
1. Commit with the conventional format

**Never:**

- Add `Co-Authored-By` lines
- Add emoji prefixes
- Use past tense in subjects ("added" → "add")
- Exceed 72 characters in the subject line

### `/git branch <name>`

1. Ensure working tree is clean (`git status`)
1. Create a properly named branch: `feat/<description>`, `fix/<description>`, `refactor/<description>`
1. Switch to the new branch
1. Report the branch name

### `/git rebase`

1. Fetch latest: `git fetch origin main`
1. Rebase onto main: `git rebase origin/main`
1. If conflicts arise, resolve them one commit at a time, then `git rebase --continue`
1. Never force-push to main

### `/git squash [n]`

Squash the last `n` commits into one:

1. Mark all but the first commit as `squash` in the interactive rebase
1. Combine the commit messages, keeping the most descriptive subject
1. Write a clean conventional commit message for the result

If `n` is not specified, squash all commits on the current branch that are not on `main`.

### `/git merge`

Merge a PR using GitHub squash merge (branch protection prevents direct push to
main):

1. Ensure CI passes: `gh pr checks <number>`
1. Merge: `gh pr merge <number> --squash --delete-branch`
1. Pull the result: `git checkout main && git pull`

GitHub squash merge creates a single commit on main. Configure GPG signing in
GitHub settings so squash merges are signed.

### `/git log [n]`

Show the last `n` commits (default 10) in a clean format:

```bash
git log --oneline --graph --decorate -n ${1:-10}
```

### `/git diff [target]`

Show a meaningful diff:

- If `target` is a branch, diff against that branch
- If no target, diff against `main`
- Always use `--stat` first for an overview, then full diff if needed

### `/git status`

Show working tree status with a focus on what matters:

- Staged changes (ready to commit)
- Unstaged changes (need review before staging)
- Untracked files (need triage)

### `/git fixup`

Create a fixup commit for the most recent commit:

1. Stage only the changed files
1. Commit with `--fixup=HEAD`
1. This marks the commit for later squashing with `git rebase --autosquash`

### `/git fixup [hash]`

Create a fixup commit for a specific earlier commit:

1. Stage only the changed files
1. Commit with `--fixup=<hash>`

## Best Practices

- **Commit early, commit often** — small, atomic commits are easier to review, revert, and bisect
- **Never commit secrets** — `.env` files, API keys, tokens, credentials
- **Never force-push to main** — rebase feature branches, protect main
- **Review your own diff before committing** — `git diff --staged` is the last line of defense
- **Write the commit message last** — after seeing the full diff, not before
- **Separate concerns** — a commit that fixes a bug and also reformats whitespace is two commits
- **Keep branches short-lived** — merge within days, not weeks
- **Merge via `gh pr merge --squash`** — branch protection prevents direct push to main; configure GPG in GitHub for signed squash merges

## What NOT To Do

- Never add `Co-Authored-By` lines or AI attribution to commits
- Never use `git add .` or `git add -A` — stage specific files
- Never push with `--force` to main
- Never commit `.env` files, credentials, or secrets
- Never use `--no-verify` to skip hooks
- Never write past-tense subjects ("fixed" instead of "fix")
- Never write vague subjects like "update stuff" or "misc changes"
- Never mix refactoring and feature changes in one commit
- Never leave merge commits from `git pull` — use `git pull --rebase`
- Never use GitHub rebase merge — creates unsigned commits; use squash merge with GPG configured in GitHub
