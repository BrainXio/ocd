---

## name: terraform description: "Write, refactor, and audit Terraform/OpenTofu IaC with state hygiene, no hardcoded secrets, and composable modules. Use when creating, reviewing, or fixing .tf files, modules, state, or provider configs." argument-hint: "[file path or 'audit' or 'plan']"

# Terraform / OpenTofu Skill

You are an IaC expert who writes clean, composable, secure Terraform/OpenTofu following these conventions. The rules apply equally to both tools — use `terraform` or `tofu` interchangeably based on the project's choice of CLI.

## Mandatory Rules

- Use HCL2 — no JSON syntax for resource definitions
- Every resource must have a `tags` or `labels` attribute that includes `Name` and `Environment` (or provider equivalent)
- Never hardcode secrets — use variables, vault references, or environment variables
- Always run `terraform fmt` before committing — zero tolerance for formatting drift
- Always run `terraform validate` after changes — zero tolerance for validation errors

## Critical Rules

### State Hygiene

- Store state remotely — never use local state in production
- Enable state locking on all remote backends
- Use `workspace` for environment separation (dev/staging/prod), not directory duplication
- Use `data` sources to read existing resources — never hardcode IDs or ARNs
- Run `terraform plan` before every `apply` — review the diff
- Never edit state files manually — use `terraform state` commands
- Use `lifecycle` blocks to prevent accidental destruction: `prevent_destroy`, `ignore_changes`

### Module Design

- One module per concern — networking, compute, database, monitoring are separate modules
- Use `variables.tf` for inputs, `outputs.tf` for outputs, `main.tf` for resources — consistent file layout
- Every variable must have a `description` and `type` — use `default` only when safe
- Use `object` types for complex inputs instead of loose `map(any)`
- Use `nullable = false` for required variables
- Every output must have a `description` and `value`
- Set `version` constraints on all module sources: `source = "...?ref=v1.2.3"`
- Use `count` and `for_each` for resource iteration — never copy-paste similar resources
- Use `dynamic` blocks for repeated nested configurations

### Provider and Backend Config

- Pin provider versions with `>= x.y.z, < x.(y+1).0` — never use unversioned providers
- Use `required_providers` in `terraform` block — never rely on implicit provider installs
- Use `required_version` to pin Terraform/OpenTofu CLI version
- Use separate backends per environment — never share state between dev and prod
- Pass provider configuration explicitly via `providers` block in module calls when multi-provider

### Security

- Never commit `.tfvars` files with real values — use `.gitignore` and pass values via environment variables or vault
- Use `sensitive = true` on all variables that contain secrets, tokens, or passwords
- Use `nonsensitive()` only in outputs that need to display non-sensitive derived values
- Use `aws_kms_secrets` or equivalent for encrypting secrets in state
- Mark outputs that expose sensitive data with `sensitive = true`
- Use `lifecycle { prevent_destroy = true }` on resources that must not be destroyed (databases, S3 buckets with data)
- Use least-privilege IAM policies — no `Action: *` or `Resource: *`

### Naming and Organization

- Use `snake_case` for all resource names, variable names, and output names
- Use the naming pattern: `{project}-{environment}-{resource-type}-{descriptor}` (e.g., `ocd-prod-s3-logs`)
- Group related resources in the same file: `vpc.tf`, `rds.tf`, `s3.tf`
- Use `locals` for computed values and naming conventions — never repeat logic
- Use `terraform_remote_state` to reference outputs from other workspaces — never hardcode

## Linting / Validation

```bash
# Format
terraform fmt -recursive -check

# Validate
terraform validate

# Security scan (if available)
tfsec .

# Cost estimation (if available)
infracost breakdown --path=.
```

## Anti-Patterns to Avoid

- Hardcoded secrets in `.tf` files — use variables with `sensitive = true` or external secret stores
- `terraform apply` without `terraform plan` — always review the diff first
- Copy-pasting resource blocks — use modules or `for_each`
- `depends_on` without a clear reason — use implicit references whenever possible
- `default = []` or `default = {}` for required complex types — use `nullable = false` instead
- Ignoring drift — run `terraform plan` regularly and address changes
- Using `count.index` as a resource identifier — use `for_each` with meaningful keys
- Provider blocks in modules — pass providers via `providers` map in module calls
- `ignore_changes = all` — be specific about which attributes to ignore
