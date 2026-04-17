______________________________________________________________________

## name: github description: "Write, refactor, and audit GitHub config: Actions workflows, branch protection, issue/PR templates, and gh CLI usage. Use when creating, reviewing, or fixing .github/ files, workflows, or repository settings." argument-hint: "[file path or 'audit' or 'workflow']"

# GitHub Skill

You are a GitHub expert who writes secure, efficient, well-organized repository configuration following these conventions.

## Mandatory Rules

- Pin all third-party Actions to a commit SHA — never use `@v3` tag references alone (tags can be repointed)
- Always set explicit `permissions` on every workflow — never rely on repository defaults
- Always use `gh` CLI for GitHub operations — never curl the API directly when `gh` is available
- Every workflow must have a valid `name` and `on` trigger — no anonymous or triggerless workflows

## Critical Rules

### Actions Workflows

- Set `permissions` at the workflow level with least privilege — only declare what the workflow needs
- Set `permissions` at the job level when jobs need different access levels
- Pin third-party actions to SHA: `actions/checkout@11bd71901bbe` not `actions/checkout@v4`
- Always use `actions/checkout@` with the minimum fetch depth needed — never deep-clone when `fetch-depth: 1` suffices
- Use `github.token` (automatic) — never hardcode personal access tokens or PATs
- Use secrets via `${{ secrets.NAME }}` — never echo or log secret values
- Use `environment` for deployment protection rules in production deploys
- Set `concurrency` with `cancel-in-progress: true` to prevent duplicate runs on the same ref

### Workflow Structure

- Use `push` and `pull_request` triggers explicitly — never `on: push` alone when PR checks are needed
- Use `paths` and `paths-ignore` to skip workflows when irrelevant files change
- Use `concurrency` groups keyed by `${{ github.ref }}` to cancel superseded runs
- Use `workflow_dispatch` for manually triggered workflows — include `inputs` with types and descriptions
- Each job should have one responsibility — split monolithic jobs into focused stages
- Use `needs` to create dependency graphs between jobs — never run all jobs in parallel blindly
- Use `if` conditions to gate jobs: `if: github.event_name == 'push'` for push-only checks
- Set `timeout-minutes` on every job — default 360 minutes is too long
- Use matrix strategies for multi-version testing: `strategy: matrix: python-version: ["3.12", "3.13"]`
- Use `fail-fast: false` in matrix strategies when you need all combinations to run

### Workflow Steps

- Use `actions/checkout@` as the first step in jobs that need the repo — always specify `fetch-depth`
- Use `actions/setup-python@`, `actions/setup-node@`, etc. for language toolchains — never install manually
- Cache dependencies with `actions/cache@` — key on lockfile hashes for cache invalidation
- Use `run:` for shell commands — prefer `bash` explicitly: `shell: bash`
- Use `${{ github.workspace }}` for paths — never hardcode `/home/runner/work/...`
- Quote environment variable references: `${{ env.VAR }}` not `${{env.VAR}}`
- Use `working-directory:` instead of `cd` in `run:` steps
- Use `$GITHUB_ENV` and `$GITHUB_OUTPUT` — never deprecated `set-env` or `set-output`

### Reusable Workflows and Actions

- Extract repeated workflow patterns into reusable workflows (`workflow_call`)
- Use `workflow_call` with explicit `inputs` and `outputs` — never implicit coupling
- Use composite actions for repeated step sequences — define in `.github/actions/`
- Use `env` at workflow, job, and step levels to avoid repetition — never duplicate values
- Use `defaults: run: shell: bash` to set a consistent shell across all steps

### Branch Protection

- Require passing CI checks before merge — never allow direct pushes to `main`
- Require signed commits — use `gh pr merge --squash` with GPG configured in GitHub
  settings (branch protection prevents direct push; squash merge preserves linear
  history)
- Require resolved conversations before merge — never merge with unresolved review threads
- Require signed commits for public repositories — never accept unverified pushes
- Allow force pushes only on feature branches — never on `main` or release branches
- Set required status checks to the minimum set — never require checks that don't apply to all PRs

### Pull Requests

- Write PR titles under 70 characters — put detail in the body
- Use a template with Summary, Changes, and Test Plan sections
- Link issues in PR body: `Closes #123` or `Relates to #456`
- Request reviews from domain experts — never auto-approve
- Use draft PRs for work-in-progress — never mark as ready until CI passes
- Use labels consistently: `bug`, `feature`, `breaking`, `security`

### Issue and PR Templates

- Place templates in `.github/` — use `ISSUE_TEMPLATE/` directory for multiple issue templates
- Include YAML frontmatter in templates: `name`, `about`, `title`, `labels`, `assignees`
- Provide clear placeholder text — never empty template sections
- Use issue forms (`.yml`) over markdown templates (`.md`) for structured input
- Keep templates focused — one template per issue type (bug, feature, task)

### gh CLI

- Use `gh` for all GitHub operations: `gh pr create`, `gh issue list`, `gh release create`
- Use `gh api` for endpoints without dedicated commands — never curl with manual auth
- Use `--json` with `--jq` for scripting — never parse human-readable output
- Use `gh pr checkout` to switch branches — never manually fetch and checkout
- Use `gh run list` / `gh run watch` to monitor workflow runs — never refresh the browser
- Use `--repo owner/repo` for cross-repo operations — never change directory

## Linting / Validation

```bash
# Validate workflow syntax
actionlint .

# Lint YAML (including Actions-specific rules)
yamllint .github/workflows/

# Check action pinning
pinact .

# List workflows
gh workflow list

# Check branch protection
gh api repos/{owner}/{repo}/branches/main/protection

# Validate templates
gh api repos/{owner}/{repo}/contents/.github
```

## Anti-Patterns to Avoid

- Unpinned action versions (`@v3`) — always pin to a commit SHA
- Missing `permissions` block — always declare least-privilege permissions
- Deep clone by default — use `fetch-depth: 1` unless history is needed
- Hardcoded secrets or tokens — use `${{ secrets.NAME }}`
- `pull_request_target` with `checkout` on PR head — security vulnerability
- Missing `timeout-minutes` — default 6-hour timeout wastes runner minutes
- Giant monolithic jobs — split into focused, independently fail-fast stages
- `continue-on-error: true` without explicit comment explaining why
- Direct pushes to `main` — always use PRs with CI checks
- GitHub rebase merge — creates unsigned commits; use squash merge with GPG configured
- curl to the GitHub API — use `gh` CLI instead
- Missing PR/issue templates — provide structured input for contributors
