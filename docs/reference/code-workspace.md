---
title: Code Workspace
aliases: [workspace, vscode, code-workspace]
tags: [reference]
created: 2026-04-17
updated: 2026-04-17
---

How the `ocd.code-workspace` file configures VS Code for this project, what each setting does, and why it's structured this way.

## What It Is

`ocd.code-workspace` is a VS Code multi-root workspace file. Opening it with `code ocd.code-workspace` loads the project with folder shortcuts and shared editor settings — no manual configuration required.

## Folders

The workspace exposes five root folders:

| Folder           | Purpose                                   |
| ---------------- | ----------------------------------------- |
| `.`              | Project root: source, tests, docs, config |
| `USER/daily`     | Daily session logs                        |
| `USER/knowledge` | Compiled knowledge articles               |
| `USER/reports`   | Lint and audit reports                    |
| `USER/.state`    | Temporary context files from hooks        |

The `USER/` folders give quick access to the knowledge pipeline's data without cluttering the root view. These are gitignored directories — each instance has its own data.

## Settings

Each setting is a single-source-of-truth decision that matches a project standard:

| Setting                                                          | Value                                                | Why                                                   |
| ---------------------------------------------------------------- | ---------------------------------------------------- | ----------------------------------------------------- |
| `editor.formatOnSave`                                            | `true`                                               | Catches formatting issues before the lint hook does   |
| `editor.insertSpaces`                                            | `true`                                               | Python convention (PEP 8)                             |
| `editor.rulers`                                                  | `[100]`                                              | Matches `ruff` line-length in `pyproject.toml`        |
| `editor.tabSize`                                                 | `4`                                                  | Python standard indentation                           |
| `files.insertFinalNewline`                                       | `true`                                               | POSIX convention; required by mdformat and shellcheck |
| `files.trimTrailingWhitespace`                                   | `true`                                               | Prevents noisy diffs from trailing whitespace         |
| `files.exclude`                                                  | `__pycache__`, `.ruff_cache`, `.venv`, `.mypy_cache` | Hides generated files from the explorer tree          |
| `search.exclude`                                                 | `__pycache__`, `.venv`, `uv.lock`                    | Keeps search results relevant                         |
| `[python] organizeImportsOnSave`                                 | `explicit`                                           | Keeps import blocks sorted; matches ruff's `I` rule   |
| `[markdown] wordWrap`                                            | `on`                                                 | Readable editing for docs and knowledge articles      |
| `python.analysis.typeCheckingMode`                               | `strict`                                             | Matches `mypy --strict` in CI                         |
| `python.analysis.diagnosticSeverityOverrides.reportUnusedImport` | `warning`                                            | Ruff catches this too; avoids duplicate errors        |

## Extension Recommendations

Extension recommendations live in `.vscode/extensions.json` (gitignored). Each developer self-determines which extensions to install — VS Code prompts on repo open, but the choice is personal.

Suggested extensions:

| Extension                        | Purpose                                 |
| -------------------------------- | --------------------------------------- |
| `ms-python.python`               | Python language support                 |
| `charliermarsh.ruff`             | Linting, formatting, and import sorting |
| `ms-python.mypy-type-checker`    | Strict type checking                    |
| `timonwong.shellcheck`           | Shell script linting                    |
| `DavidAnson.vscode-markdownlint` | Markdown linting                        |
| `redhat.vscode-yaml`             | YAML validation and formatting          |
| `Anthropic.claude-code`          | Claude Code integration                 |

## Why a Workspace File Instead of `.vscode/settings.json`

The workspace file is version-controlled and shared across all developers. It contains only project standards — settings that must be consistent (ruler position, formatting rules, type checking mode). Personal preferences (theme, keybindings, individual extensions) belong in `.vscode/`, which is gitignored.

This follows the project's Single Source of Truth standard: `pyproject.toml` owns Python tooling config, `ocd.code-workspace` owns editor config, `.claude/settings.json` owns Claude Code config. No duplication.

## How to Use

```bash
code ocd.code-workspace
```

VS Code opens with all five folders in the sidebar and all settings applied. To customize extensions, create `.vscode/extensions.json` — VS Code will prompt you with recommendations on first open.
