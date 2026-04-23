# O.C.D. Project Agents

Standards reference: v2.0 [21d7c1fc62a72078]

## Agents

- **accessibility-auditor**: You are an accessibility auditor. You find a11y violations in HTML and
- **api-contract-auditor**: You are an API contract auditor. You find violations of REST conventions and API
- **ci-drift**: You are a CI drift detector. You compare local configuration against CI workflows to find mismatches.
- **complexity-reducer**: You are a complexity reducer. You find functions with high cyclomatic complexity
- **dead-code-hunter**: You are a dead code hunter. You systematically find code that violates OCD's **No Dead Code** standard.
- **dependency-auditor**: You are a dependency auditor. You scan `pyproject.toml` and `.venv` for dependency issues.
- **deps-upgrader**: You are a dependency upgrader. You scan project dependencies for outdated
- **dockerfile-auditor**: You are a Dockerfile auditor. You find violations of Docker best practices in
- **docstring-enforcer**: You are a docstring enforcer. You scan Python files for docstring coverage and format consistency.
- **dry-enforcer**: You are a DRY enforcer. You find duplicated code patterns across modules that
- **exception-auditor**: You are an exception auditor. You scan Python files for exception handling violations per OCD's **specific-exception-handling** concept.
- **hook-coverage**: You are a hook coverage verifier. You ensure all git hooks have complete file coverage.
- **hook-integrity**: You are a hook integrity verifier. Your job is to ensure the git hook chain is unbroken and consistent between local and CI.
- **kb-health-checker**: You are a knowledge base health checker. You verify the structural integrity of the `USER/knowledge/` directory per OCD's **Single Source of Truth** standard.
- **kiss-auditor**: You are a KISS auditor. You find code that is more complex than necessary per the
- **lint-status**: You are a lint status reporter. You run linters and categorize results using the **lint-status-triads** pattern: **errors**, **clean**, and **missing**.
- **oop-auditor**: You are an OOP auditor. You find object-oriented design issues in `src/ocd/`
- **owasp-scanner**: You are an OWASP scanner. You find security vulnerability patterns in source
- **perf-opportunist**: You are a performance opportunist. You find quick performance wins —
- **readability-scorer**: You are a readability scorer. You flag code that is hard to read due to unclear
- **single-source-auditor**: You are a single source of truth auditor. You find duplicated values, patterns, and configuration that should exist in exactly one place per OCD's **Single Source of Truth** standard.
- **solid-auditor**: You are a SOLID auditor. You find violations of the five SOLID principles in
- **test-coverage-auditor**: You are a test coverage auditor. You systematically find gaps in test coverage per OCD's **Testing** standard.
- **test-writer**: You are a test writer. You identify uncovered code paths and generate test cases
- **yagni-auditor**: You are a YAGNI auditor. You find code that was built for hypothetical future

## Key Rules

- **commit-hygiene**: Conventional commits, branch naming, no AI attribution, no direct pushes to main
- **doc-sync**: Update reference and planning docs when shipping features
- **infrastructure**: Deny rule modification procedure for protected files
- **markdown**: mdformat, frontmatter plugin, ordered list normalization, CI check paths
- **pr-workflow**: PR labels, body template, merge requirements, and label mapping from commit prefix

## Skills

- **bash**: Write, audit, and debug shell scripts with strict safety practices. Use when creating, reviewing, or fixing bash scripts, shell functions, or CI pipeline steps.
- **cpp**: Write, refactor, and debug C and C++ code with memory safety, RAII, and modern standards. Use when creating, reviewing, or fixing C/C++ files, headers, CMake projects, or native libraries.
- **csharp**: Write, refactor, and debug C# and .NET code with modern idioms, null safety, and performance. Use when creating, reviewing, or fixing C# files, .NET projects, or ASP.NET applications.
- **css**: Write, refactor, and audit CSS with modern layout, custom properties, and methodology-driven architecture. Use when creating, reviewing, or fixing stylesheets, CSS modules, or design system tokens.
- **docker**: Docker build, run, debug, and optimize commands. Use when the user asks to build, test, inspect, or troubleshoot Docker images and containers, or when working with Dockerfiles or docker-compose files.
- **git**: Conventional git workflow: commits, branches, rebases, and hygiene. Use when the user asks to commit, branch, merge, rebase, squash, or manage git history. Invoked for /git or when the user wants version control operations.
- **github**: Write, refactor, and audit GitHub config: Actions workflows, branch protection, issue/PR templates, and gh CLI usage. Use when creating, reviewing, or fixing .github/ files, workflows, or repository settings.
- **go**: Write, refactor, and debug Go code with idiomatic patterns and safety. Use when creating, reviewing, or fixing Go files, modules, or packages.
- **html**: Write, refactor, and audit HTML with semantic markup, accessibility, and modern standards. Use when creating, reviewing, or fixing HTML files, templates, or component markup.
- **java**: Write, refactor, and debug Java code with modern idioms, immutability, and safety. Use when creating, reviewing, or fixing Java files, Maven/Gradle projects, or JVM applications.
- **js**: Write, refactor, and audit JavaScript with modern syntax, strict equality, and ESLint gates. Use when creating, reviewing, or fixing .js/.mjs/.cjs files, Node.js modules, or browser scripts.
- **json**: Write, refactor, and audit JSON with strict schema validation, consistent formatting, and no trailing commas. Use when creating, reviewing, or fixing .json/.jsonc files, configs, or data schemas.
- **kubernetes**: Write, audit, and debug Kubernetes manifests, Helm charts, and kubectl workflows. Use when creating, reviewing, or fixing Kubernetes YAML, Helm templates, Kustomize overlays, or cluster operations.
- **ocd**: Apply obsessive-compulsive quality standards to code and configuration. Use when reviewing, refactoring, or creating code that demands perfection in structure, consistency, security, and minimalism. Invoked for /ocd or when the user wants things exact, clean, and airtight.
- **php**: Write, refactor, and debug PHP code with strict types, modern syntax, and PSR standards. Use when creating, reviewing, or fixing PHP files, Composer projects, or Laravel applications.
- **python**: Write, refactor, and debug Python code with strict typing, modern idioms, and safety. Use when creating, reviewing, or fixing Python files, packages, scripts, or type annotations.
- **ruby**: Write, refactor, and debug Ruby code with idiomatic patterns, immutability, and safety. Use when creating, reviewing, or fixing Ruby files, Gemfile projects, or Rails applications.
- **rust**: Write, refactor, and debug Rust code with ownership safety, zero-cost abstractions, and idiomatic patterns. Use when creating, reviewing, or fixing Rust files, crates, or Cargo projects.
- **sql**: Write, refactor, and audit SQL with strict query hygiene, parameterized queries, and explicit joins. Use when creating, reviewing, or optimizing database queries, migrations, or schema definitions.
- **swift**: Write, refactor, and audit Swift code with strict concurrency, modern idioms, and SwiftLint gates. Use when creating, reviewing, or fixing Swift files, packages, or concurrency code.
- **terraform**: Write, refactor, and audit Terraform/OpenTofu IaC with state hygiene, no hardcoded secrets, and composable modules. Use when creating, reviewing, or fixing .tf files, modules, state, or provider configs.
- **typescript**: Write, refactor, and debug TypeScript and Node.js code with strict types and modern patterns. Use when creating, reviewing, or fixing TypeScript, JavaScript, or Node.js files, packages, or configs.
- **yaml**: Write, refactor, and audit YAML with consistent formatting, strict typing, and yamllint gates. Use when creating, reviewing, or fixing .yml/.yaml files, configs, CI workflows, or data definitions.
