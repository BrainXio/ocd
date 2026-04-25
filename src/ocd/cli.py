"""OCD umbrella CLI — all commands under `ocd <subcommand>`.

Hook invocations (session-start, format-work, etc.) are routed through
`ocd hook <name>`. Everything else is dispatched through this module
via `ocd <subcommand>`.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from ocd.config import (
    CONCEPTS_DIR,
    CONNECTIONS_DIR,
    DAILY_DIR,
    DEFAULT_INDEX_CONTENT,
    INDEX_FILE,
    KB_INJECTION_COUNT,
    KNOWLEDGE_DB,
    KNOWLEDGE_DIR,
    PROJECT_ROOT,
    QA_DIR,
    REPORTS_DIR,
    RESOURCES_DIR,
    STATE_DIR,
    USER_DIR,
)
from ocd.fix.format import run_formatters

TEMPLATES_DIR = Path("/opt/ocd/templates")

VENDOR_DIRS = [
    ".aider",
    ".cursor/rules",
    ".github/instructions",
    ".windsurf/rules",
    ".amazonq/rules",
]

USER_DIRS = [
    str(p.relative_to(PROJECT_ROOT))
    for p in [
        DAILY_DIR,
        CONCEPTS_DIR,
        CONNECTIONS_DIR,
        QA_DIR,
        RESOURCES_DIR,
        REPORTS_DIR,
        STATE_DIR,
        USER_DIR / "logs",
        USER_DIR / "agents" / "tasks",
        USER_DIR / "agents" / "runtime",
        USER_DIR / "cache",
    ]
]

USER_GITIGNORE = """\
# Ignore everything in USER/ (private runtime data)
*
# Except this .gitignore itself
!.gitignore
# And subdirectories (so git can traverse into them)
!*/
"""


# ── Subcommand handlers ─────────────────────────────────────────────────────


def _cmd_init(_args: argparse.Namespace) -> None:
    """Initialize the OCD environment."""
    project_dir = Path.cwd()
    project = _detect_project(project_dir)

    _init_agent_dir(project_dir)
    _init_vendor_dirs(project_dir)

    copied = _copy_templates(project_dir)
    if copied:
        print("Seeded OCD templates:")
        for item in copied:
            print(f"  + {item}")
    elif TEMPLATES_DIR.is_dir():
        print("OCD templates already present, skipping.")

    if project["python"]:
        print("→ Installing Python dependencies…")
        result = subprocess.run(["uv", "sync"], check=False)
        if result.returncode != 0:
            print(f"✗ uv sync failed (exit {result.returncode})", file=sys.stderr)
            sys.exit(result.returncode)

    if project["node"]:
        print("→ Installing Node.js dependencies…")
        result = subprocess.run(["npm", "ci"], check=False)
        if result.returncode != 0:
            print(f"✗ npm ci failed (exit {result.returncode})", file=sys.stderr)
            sys.exit(result.returncode)

    hooks_script = project_dir / ".githooks" / "setup-hooks.sh"
    if hooks_script.exists() and project["git"]:
        print("→ Installing git hooks…")
        result = subprocess.run(["bash", str(hooks_script)], check=False)
        if result.returncode != 0:
            print(f"✗ Git hooks failed (exit {result.returncode})", file=sys.stderr)
            sys.exit(result.returncode)

    print("OCD environment initialized.")


def _cmd_shell(_args: argparse.Namespace) -> None:
    """Start an interactive shell with the OCD environment."""
    shell = os.environ.get("SHELL", "/bin/bash")
    if not _is_valid_shell(shell):
        shell = "/bin/bash"
    os.execvp(shell, [shell])  # nosemgrep: dangerous-os-exec-tainted-env-args


def _cmd_format(_args: argparse.Namespace) -> None:
    """Run all formatters with auto-fix."""
    sys.exit(run_formatters())


def _cmd_kb(args: argparse.Namespace) -> None:
    """Handle kb subcommands."""
    if args.kb_command == "query":
        from ocd.kb.relevance import (
            build_kb_index_json,
            score_articles,
        )

        index = build_kb_index_json(use_db=True)
        if args.vectors:
            from ocd.kb.relevance import hybrid_score_articles

            scored = hybrid_score_articles(
                args.relevant_to,
                index,
                db_path=KNOWLEDGE_DB,
                top_k=args.top_k or KB_INJECTION_COUNT,
            )
        else:
            scored = score_articles(args.relevant_to, index, top_k=args.top_k or KB_INJECTION_COUNT)

        if not scored:
            print("No relevant articles found.")
            return

        print(f"Top {len(scored)} articles for: '{args.relevant_to}'\n")
        for entry in scored:
            score_str = f" ({entry['score']:.2f})" if entry.get("score", 0) > 0 else ""
            title = entry.get("title", entry["path"])
            summary = entry.get("summary", "")
            print(f"  {title}{score_str}")
            if summary:
                print(f"    {summary}")
            print(f"    → {entry['path']}")
            print()
    else:
        print(f"Unknown kb subcommand: {args.kb_command}", file=sys.stderr)
        sys.exit(1)


def _cmd_route(args: argparse.Namespace) -> None:
    """Route a task to the best-matching agent."""
    from ocd.routing.router import build_manifest, load_manifest, route_query, save_manifest

    if args.build_manifest:
        print("Building agent manifest...")
        manifest = build_manifest()
        path = save_manifest(manifest)
        print(f"Manifest saved to {path} ({len(manifest['agents'])} agents)")
        return

    loaded = load_manifest()
    if loaded is None:
        print("Building agent manifest (first time)...", file=sys.stderr)
        loaded = build_manifest()
        save_manifest(loaded)

    query_text = " ".join(args.query) if args.query else ""
    if not query_text:
        print("error: route requires a query", file=sys.stderr)
        sys.exit(2)

    results = route_query(query_text, loaded, args.max)
    if not results:
        print("No matching agents found.")
        return

    for entry in results:
        print(f"  {entry['name']} (score: {entry['score']})")


def _cmd_standards(args: argparse.Namespace) -> None:
    """Manage standards hash reference."""
    from ocd.routing.standards import update_standards_hash, verify_standards_hash

    if args.verify:
        result = verify_standards_hash()
        if result.get("error"):
            print(f"error: {result['error']}", file=sys.stderr)
            sys.exit(1)
        if result["match"]:
            print(f"ok: standards v{result['version']} [{result['computed_hash']}]")
        else:
            print(
                f"mismatch: stored={result['stored_hash']}, computed={result['computed_hash']}",
                file=sys.stderr,
            )
            sys.exit(1)
    elif args.update:
        new_hash = update_standards_hash()
        if new_hash:
            print(f"updated: {new_hash}")
        else:
            print("error: could not update standards hash", file=sys.stderr)
            sys.exit(1)
    else:
        print("error: specify --verify or --update", file=sys.stderr)
        sys.exit(2)


def _cmd_fix(args: argparse.Namespace) -> None:
    """Closed-loop fix commands."""
    from ocd.fix.cycle import fix_cycle, lint_and_fix, security_scan_and_patch, test_and_fix

    command = args.fix_command
    if command == "fix-cycle":
        if not args.files:
            print("error: fix-cycle requires at least one file", file=sys.stderr)
            sys.exit(2)
        r = fix_cycle(args.files[0])
    elif command == "lint-and-fix":
        path = args.files[0] if args.files else "src/"
        r = lint_and_fix(path)
    elif command == "test-and-fix":
        r = test_and_fix()
    elif command == "security-scan-and-patch":
        r = security_scan_and_patch()
    else:
        print(f"error: unknown fix command: {command}", file=sys.stderr)
        sys.exit(2)
    print(r.to_json())
    sys.exit(r.exit_code)


def _cmd_check(_args: argparse.Namespace) -> None:
    """Fast local quality gate."""
    from ocd.gates.check import run_check

    sys.exit(run_check())


def _cmd_ci_check(args: argparse.Namespace) -> None:
    """Full local CI mirror."""
    from ocd.gates.ci_check import run_ci_check

    sys.exit(run_ci_check(fast=args.fast, commit_range=args.commit_range))


def _cmd_verify_commit(args: argparse.Namespace) -> None:
    """Verify commit messages."""
    from ocd.gates.verify_commit import check_commit_range, check_message

    if args.message:
        msg_violations = check_message(args.message)
        if msg_violations:
            for pattern, line in msg_violations:
                print(f"error: AI attribution pattern '{pattern}' found: {line}", file=sys.stderr)
            sys.exit(1)
        print("ok: commit message is clean")
    elif args.range_spec:
        range_violations = check_commit_range(args.range_spec)
        if range_violations:
            for commit_hash, _pattern, line in range_violations:
                print(
                    f"error: commit {commit_hash[:8]} contains prohibited AI attribution: {line}",
                    file=sys.stderr,
                )
            sys.exit(1)
        print("ok: no AI attribution patterns found in commit range")
    elif args.msg_file:
        from pathlib import Path

        msg = Path(args.msg_file).read_text(encoding="utf-8")
        violations = check_message(msg)
        if violations:
            for _pattern, line in violations:
                print(f"error: commit message contains AI attribution: {line}", file=sys.stderr)
            print("", file=sys.stderr)
            print("Remove the attribution line and retry.", file=sys.stderr)
            print("Patterns: .githooks/ai-patterns.txt", file=sys.stderr)
            sys.exit(1)
        print("ok: commit message is clean")
    else:
        print("error: specify --message, --range, or a msg_file", file=sys.stderr)
        sys.exit(2)


def _cmd_scan_secrets(args: argparse.Namespace) -> None:
    """Scan for secrets in source code."""
    from ocd.gates.scan_secrets import scan_secrets

    result = scan_secrets(staged=args.staged, source=args.source)
    sys.exit(result)


def _cmd_materialize(args: argparse.Namespace) -> None:
    """Materialize .claude/ content from database to target directory."""
    from ocd.packaging.materialize import run_materialize

    sys.exit(
        run_materialize(
            target=args.target,
            db=args.db,
            force=args.force,
            vendor=args.vendor,
            docs_dir=args.docs_dir,
            include=args.include,
            all_skills=args.all_skills,
            minimal=args.minimal,
        )
    )


def _cmd_compile(args: argparse.Namespace) -> None:
    """Compile daily logs into knowledge articles."""
    from ocd.kb.compile import run_compile

    sys.exit(
        run_compile(
            all_logs=args.all,
            file=args.file,
            dry_run=args.dry_run,
            manifest=args.manifest,
            update_standards_hash=args.update_standards_hash,
        )
    )


def _cmd_export(args: argparse.Namespace) -> None:
    """Export knowledge base to Obsidian-compatible markdown vault."""
    from ocd.kb.export import run_export

    db_path = Path(args.db) if args.db else None
    sys.exit(
        run_export(
            output=args.output,
            commit=args.commit,
            force=args.force,
            dry_run=args.dry_run,
            db_path=db_path,
        )
    )


def _cmd_ingest(args: argparse.Namespace) -> None:
    """Ingest wiki articles into knowledge.db."""
    from ocd.kb.ingest import ingest_raw

    result = ingest_raw(force_all=args.all, dry_run=args.dry_run)
    print(result.to_json())
    sys.exit(1 if result.errors else 0)


def _cmd_knowledge(args: argparse.Namespace) -> None:
    """Handle knowledge subcommands."""
    if args.knowledge_command == "status":
        from ocd.kb.ingest import kb_status

        status = kb_status()
        print(f"KB status: {status['db_count']} articles in DB, {status['disk_count']} on disk")
        if status["new"]:
            print(f"  {len(status['new'])} new (not yet ingested): {', '.join(status['new'][:5])}")
            if len(status["new"]) > 5:
                print(f"    ... and {len(status['new']) - 5} more")
        if status["stale"]:
            print(
                f"  {len(status['stale'])} stale (mtime changed): {', '.join(status['stale'][:5])}"
            )
        if status["orphaned"]:
            print(
                f"  {len(status['orphaned'])} orphaned (in DB but not on disk): "
                f"{', '.join(status['orphaned'][:5])}"
            )
        if status["last_ingest"]:
            print(f"Last ingest: {status['last_ingest']}")
        sys.exit(0 if status["synced"] else 1)
    else:
        print(f"Unknown knowledge subcommand: {args.knowledge_command}", file=sys.stderr)
        sys.exit(1)


def _cmd_vec(args: argparse.Namespace) -> None:
    """Handle vec subcommands."""
    from ocd.kb.vec import run_vec_rebuild, run_vec_search, run_vec_status

    if args.vec_command == "rebuild":
        sys.exit(run_vec_rebuild(force=args.force))
    elif args.vec_command == "search":
        results = run_vec_search(query=args.query, top_k=args.top_k)
        if not results:
            print("No results found.")
            return
        print(f"Top {len(results)} results:\n")
        for path, score in results:
            print(f"  {path} (score: {score:.4f})")
    elif args.vec_command == "status":
        status = run_vec_status()
        for key, value in status.items():
            print(f"{key}: {value}")


def _cmd_flush(args: argparse.Namespace) -> None:
    """Flush conversation context to daily log."""
    from ocd.session.flush import run_flush_standalone

    if not args.context_file or not args.session_id:
        print("error: flush requires context_file and session_id", file=sys.stderr)
        sys.exit(2)
    sys.exit(run_flush_standalone(args.context_file, args.session_id))


def _cmd_query(args: argparse.Namespace) -> None:
    """Query the personal knowledge base."""
    from ocd.kb.query import run_query

    result = run_query(question=args.question, file_back=args.file_back)
    if result:
        print(result)


def _cmd_lint_kb(args: argparse.Namespace) -> None:
    """Lint the knowledge base for structural issues."""
    from ocd.kb.lint import run_lint_kb

    sys.exit(run_lint_kb(structural_only=args.structural_only))


def _cmd_compile_db(args: argparse.Namespace) -> None:
    """Compile content into bundled SQLite database."""
    from ocd.packaging.pack import run_compile_db

    sys.exit(
        run_compile_db(output=args.output, source=args.source, portable_source=args.portable_source)
    )


def _cmd_pre_push(args: argparse.Namespace) -> None:
    """Diff-aware pre-push test runner."""
    from ocd.gates.pre_push import run_pre_push

    sys.exit(run_pre_push())


def _cmd_autofix(args: argparse.Namespace) -> None:
    """Self-corrective fix loop in isolated worktree."""
    from ocd.fix.autofix import run_autofix

    sys.exit(
        run_autofix(
            target=args.target,
            batch=args.batch,
            max_iterations=args.max_iterations,
            dry_run=args.dry_run,
        )
    )


def _cmd_worktree(args: argparse.Namespace) -> None:
    """Git worktree management — create, list, remove, status."""
    from ocd.worktree import list_worktrees, new_worktree, remove_worktree, worktree_status

    if args.worktree_command == "new":
        new_worktree(args.description, prefix=args.prefix)
    elif args.worktree_command == "list":
        worktrees = list_worktrees()
        if not worktrees:
            print("No worktrees found.")
        for wt in worktrees:
            print(f"  {wt.slug}  branch={wt.branch}  path={wt.path}")
    elif args.worktree_command == "remove":
        ok = remove_worktree(args.slug, force=args.force)
        sys.exit(0 if ok else 1)
    elif args.worktree_command == "status":
        info = worktree_status()
        if info["location"] == "worktree":
            print(f"Worktree: {info['path']}")
            print(f"Branch: {info['branch']}")
        else:
            print(f"Main tree: {info['path']}")
            print(f"Branch: {info['branch']}")
    else:
        worktree_parser = _build_parser()
        worktree_parser.parse_args(["worktree", "--help"])


# ── Hook subcommand handlers ──────────────────────────────────────────────────


def _cmd_hook_session_start(_args: argparse.Namespace) -> None:
    """SessionStart hook — inject KB context and standards reference."""
    from ocd.hooks.session_start import main as session_start_main

    session_start_main()


def _cmd_hook_session_end(_args: argparse.Namespace) -> None:
    """SessionEnd hook — capture transcript for memory extraction."""
    from ocd.hooks.session_end import main as session_end_main

    session_end_main()


def _cmd_hook_pre_compact(_args: argparse.Namespace) -> None:
    """PreCompact hook — extract context before auto-compaction."""
    from ocd.hooks.pre_compact import main as pre_compact_main

    pre_compact_main()


def _cmd_hook_format_work(args: argparse.Namespace) -> None:
    """PostToolUse format hook — auto-format edited files."""
    from ocd.hooks.format_work import edit_mode

    edit_mode()


def _cmd_hook_lint_work(args: argparse.Namespace) -> None:
    """PostToolUse/PreToolUse lint hook."""
    from ocd.hooks.lint_work import commit_mode, edit_mode

    if args.edit:
        edit_mode()
    elif args.commit:
        commit_mode()
    else:
        print("error: specify --edit or --commit", file=sys.stderr)
        sys.exit(2)


def _cmd_hook_verify_commit(args: argparse.Namespace) -> None:
    """Verify commit messages for AI attribution patterns."""
    from ocd.gates.verify_commit import check_commit_range, check_message

    if args.msg_file:
        from pathlib import Path

        msg = Path(args.msg_file).read_text(encoding="utf-8")
        violations = check_message(msg)
        if violations:
            for _pattern, line in violations:
                print(f"error: commit message contains AI attribution: {line}", file=sys.stderr)
            print("", file=sys.stderr)
            print("Remove the attribution line and retry.", file=sys.stderr)
            print("Patterns: .githooks/ai-patterns.txt", file=sys.stderr)
            sys.exit(1)
        print("ok: commit message is clean")
    elif args.range_spec:
        range_violations = check_commit_range(args.range_spec)
        if range_violations:
            for commit_hash, _pattern, line in range_violations:
                print(
                    f"error: commit {commit_hash[:8]} contains prohibited AI attribution: {line}",
                    file=sys.stderr,
                )
            sys.exit(1)
        print("ok: no AI attribution patterns found in commit range")
    elif args.message:
        msg_violations = check_message(args.message)
        if msg_violations:
            for pattern, line in msg_violations:
                print(f"error: AI attribution pattern '{pattern}' found: {line}", file=sys.stderr)
            sys.exit(1)
        print("ok: commit message is clean")
    else:
        print("error: specify msg_file, --range, or --message", file=sys.stderr)
        sys.exit(2)


def _cmd_hook_ci_check(args: argparse.Namespace) -> None:
    """Full local CI mirror."""
    from ocd.gates.ci_check import run_ci_check

    sys.exit(run_ci_check(fast=args.fast, commit_range=args.commit_range))


# ── Argument parser ─────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="ocd",
        description="OCD — Obsessive Code Discipline",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init (default)
    init_parser = subparsers.add_parser("init", help="Initialize OCD environment")
    init_parser.set_defaults(func=_cmd_init)

    # shell
    shell_parser = subparsers.add_parser("shell", help="Start interactive shell")
    shell_parser.set_defaults(func=_cmd_shell)

    # format
    fmt_parser = subparsers.add_parser("format", help="Run all formatters with auto-fix")
    fmt_parser.set_defaults(func=_cmd_format)

    # kb query
    kb_parser = subparsers.add_parser("kb", help="Knowledge base operations")
    kb_sub = kb_parser.add_subparsers(dest="kb_command", help="KB subcommands")
    kb_query = kb_sub.add_parser("query", help="Query the knowledge base")
    kb_query.add_argument("--relevant-to", required=True, help="Search query")
    kb_query.add_argument("--top-k", type=int, default=None, help="Number of results")
    kb_query.add_argument("--build-index", action="store_true", help="Rebuild index")
    kb_query.add_argument("--vectors", action="store_true", help="Use hybrid vector+TF-IDF search")
    kb_query.set_defaults(func=_cmd_kb)

    # route
    route_parser = subparsers.add_parser("route", help="Route task to best agent")
    route_parser.add_argument("query", nargs="*", help="Task description")
    route_parser.add_argument(
        "--build-manifest", action="store_true", help="Rebuild agent manifest"
    )
    route_parser.add_argument("--max", type=int, default=3, help="Max agents to return")
    route_parser.set_defaults(func=_cmd_route)

    # standards
    std_parser = subparsers.add_parser("standards", help="Manage standards hash reference")
    std_parser.add_argument("--verify", action="store_true", help="Verify hash")
    std_parser.add_argument("--update", action="store_true", help="Update hash")
    std_parser.set_defaults(func=_cmd_standards)

    # fix-cycle and aliases
    fix_parser = subparsers.add_parser("fix-cycle", help="Closed-loop fix cycle")
    fix_parser.add_argument("files", nargs="*", help="Files to fix")
    fix_parser.set_defaults(func=_cmd_fix, fix_command="fix-cycle")

    lint_fix_parser = subparsers.add_parser("lint-and-fix", help="Batch lint-and-fix")
    lint_fix_parser.add_argument("files", nargs="*", help="Directory or files")
    lint_fix_parser.set_defaults(func=_cmd_fix, fix_command="lint-and-fix")

    test_fix_parser = subparsers.add_parser(
        "test-and-fix", help="Run tests, fix if baseline passes"
    )
    test_fix_parser.add_argument("files", nargs="*", help="Test paths")
    test_fix_parser.set_defaults(func=_cmd_fix, fix_command="test-and-fix")

    sec_parser = subparsers.add_parser(
        "security-scan-and-patch", help="Semgrep scan with safe auto-fixes"
    )
    sec_parser.add_argument("files", nargs="*", help="Paths to scan")
    sec_parser.set_defaults(func=_cmd_fix, fix_command="security-scan-and-patch")

    # check
    check_parser = subparsers.add_parser("check", help="Fast local quality gate")
    check_parser.set_defaults(func=_cmd_check)

    # ci-check
    ci_parser = subparsers.add_parser("ci-check", help="Full local CI mirror")
    ci_parser.add_argument("--fast", action="store_true", help="Skip slow checks")
    ci_parser.add_argument("--commit-range", dest="commit_range", help="Git commit range")
    ci_parser.set_defaults(func=_cmd_ci_check)

    # verify-commit
    vc_parser = subparsers.add_parser("verify-commit", help="Verify commit messages")
    vc_parser.add_argument("msg_file", nargs="?", help="Commit message file")
    vc_parser.add_argument("--range", dest="range_spec", help="Git commit range")
    vc_parser.add_argument("--message", help="Single message to verify")
    vc_parser.set_defaults(func=_cmd_verify_commit)

    # scan-secrets
    ss_parser = subparsers.add_parser("scan-secrets", help="Scan for secrets")
    ss_parser.add_argument("--staged", action="store_true", help="Scan staged files only")
    ss_parser.add_argument("--source", default=".", help="Source directory")
    ss_parser.set_defaults(func=_cmd_scan_secrets)

    # materialize
    mat_parser = subparsers.add_parser("materialize", help="Materialize config from database")
    mat_parser.add_argument("--target", "-t", default=".claude", help="Target directory")
    mat_parser.add_argument("--db", default=None, help="Database path")
    mat_parser.add_argument("--force", "-f", action="store_true", help="Overwrite existing files")
    mat_parser.add_argument(
        "--vendor",
        default=None,
        help=(
            "Vendor format: aider, cursor, copilot, windsurf, amazonq, claude-code, all, agents-md"
        ),
    )
    mat_parser.add_argument(
        "--docs-dir",
        default=None,
        help="Path to docs/reference/ for creating symlinks to portable content",
    )
    mat_parser.add_argument(
        "--include",
        default=None,
        help="Comma-separated list of skill names to include (e.g., python,git)",
    )
    mat_parser.add_argument(
        "--all",
        dest="all_skills",
        action="store_true",
        help="Include all skills (default behavior)",
    )
    mat_parser.add_argument(
        "--minimal",
        action="store_true",
        help="Include only OCD core skills (rules, ocd skill, standards, settings)",
    )
    mat_parser.set_defaults(func=_cmd_materialize)

    # compile
    comp_parser = subparsers.add_parser(
        "compile", help="Compile daily logs into knowledge articles"
    )
    comp_parser.add_argument("--all", action="store_true", help="Force recompile all logs")
    comp_parser.add_argument("--file", type=str, help="Compile a specific daily log")
    comp_parser.add_argument("--dry-run", action="store_true", help="Show what would be compiled")
    comp_parser.add_argument(
        "--manifest", action="store_true", help="Rebuild agent manifest after compilation"
    )
    comp_parser.add_argument(
        "--update-standards-hash",
        action="store_true",
        help="Recompute standards.md hash",
    )
    comp_parser.set_defaults(func=_cmd_compile)

    # export
    export_parser = subparsers.add_parser("export", help="Export knowledge base to Obsidian vault")
    export_parser.add_argument(
        "--commit", action="store_true", help="Export to docs/knowledge/ (commit-friendly)"
    )
    export_parser.add_argument("--output", "-o", default=None, help="Custom output directory path")
    export_parser.add_argument(
        "--force", "-f", action="store_true", help="Overwrite existing files"
    )
    export_parser.add_argument(
        "--dry-run", action="store_true", help="Report what would be exported, no file writes"
    )
    export_parser.add_argument("--db", default=None, help="Database path (default: knowledge.db)")
    export_parser.set_defaults(func=_cmd_export)

    # ingest
    ingest_parser = subparsers.add_parser("ingest", help="Ingest wiki articles into knowledge.db")
    ingest_parser.add_argument("--all", action="store_true", help="Force re-ingest all files")
    ingest_parser.add_argument("--dry-run", action="store_true", help="Report only, no DB changes")
    ingest_parser.set_defaults(func=_cmd_ingest)

    # knowledge
    knowledge_parser = subparsers.add_parser("knowledge", help="Knowledge base operations")
    knowledge_sub = knowledge_parser.add_subparsers(
        dest="knowledge_command", help="Knowledge subcommands"
    )
    ks = knowledge_sub.add_parser("status", help="Show KB sync status")
    ks.set_defaults(func=_cmd_knowledge)

    # vec
    vec_parser = subparsers.add_parser("vec", help="Vector embedding operations")
    vec_sub = vec_parser.add_subparsers(dest="vec_command", help="Vector subcommands")
    vec_rebuild = vec_sub.add_parser("rebuild", help="Rebuild all vector embeddings")
    vec_rebuild.add_argument("--force", action="store_true", help="Force rebuild if model changed")
    vec_rebuild.set_defaults(func=_cmd_vec)
    vec_search = vec_sub.add_parser("search", help="Search knowledge base with vectors")
    vec_search.add_argument("query", help="Search query")
    vec_search.add_argument("--top-k", type=int, default=5, help="Number of results")
    vec_search.set_defaults(func=_cmd_vec)
    vec_status = vec_sub.add_parser("status", help="Show vector index status")
    vec_status.set_defaults(func=_cmd_vec)

    # flush
    flush_parser = subparsers.add_parser("flush", help="Flush conversation context to daily log")
    flush_parser.add_argument("context_file", nargs="?", help="Context file path")
    flush_parser.add_argument("session_id", nargs="?", help="Session identifier")
    flush_parser.set_defaults(func=_cmd_flush)

    # query
    q_parser = subparsers.add_parser("query", help="Query the personal knowledge base")
    q_parser.add_argument("question", help="Question to ask")
    q_parser.add_argument("--file-back", action="store_true", help="File-back results")
    q_parser.set_defaults(func=_cmd_query)

    # lint-kb
    lk_parser = subparsers.add_parser("lint-kb", help="Lint the knowledge base")
    lk_parser.add_argument(
        "--structural-only", action="store_true", help="Skip LLM checks (faster, free)"
    )
    lk_parser.set_defaults(func=_cmd_lint_kb)

    # compile-db
    cdb_parser = subparsers.add_parser("compile-db", help="Compile content into SQLite database")
    cdb_parser.add_argument("--output", "-o", default=None, help="Output database path")
    cdb_parser.add_argument(
        "--source", default=None, help="OCD content directory (default: src/ocd/content/)"
    )
    cdb_parser.add_argument(
        "--portable-source",
        default=None,
        help="Portable content directory (default: docs/reference/)",
    )
    cdb_parser.set_defaults(func=_cmd_compile_db)

    # pre-push
    pp_parser = subparsers.add_parser("pre-push", help="Diff-aware pre-push test runner")
    pp_parser.set_defaults(func=_cmd_pre_push)

    # autofix
    autofix_parser = subparsers.add_parser(
        "autofix", help="Self-corrective fix loop in isolated worktree"
    )
    autofix_parser.add_argument("target", help="File or directory path to fix")
    autofix_parser.add_argument("--batch", action="store_true", help="Use lint-and-fix strategy")
    autofix_parser.add_argument("--max-iterations", type=int, default=5, help="Max loop iterations")
    autofix_parser.add_argument("--dry-run", action="store_true", help="Report only, no merge")
    autofix_parser.set_defaults(func=_cmd_autofix)

    # worktree (nested subcommands for git worktree management)
    worktree_parser = subparsers.add_parser("worktree", help="Git worktree management")
    worktree_sub = worktree_parser.add_subparsers(
        dest="worktree_command", help="Worktree subcommands"
    )
    wt_new = worktree_sub.add_parser("new", help="Create a worktree for development")
    wt_new.add_argument("description", help="Short kebab-case description (e.g., add-search-index)")
    wt_new.add_argument(
        "--prefix",
        default="feat",
        choices=["feat", "fix", "refactor", "experiment", "docs", "test", "ci", "chore"],
        help="Branch prefix (default: feat)",
    )
    wt_new.set_defaults(func=_cmd_worktree)
    wt_list = worktree_sub.add_parser("list", help="List managed worktrees")
    wt_list.set_defaults(func=_cmd_worktree)
    wt_remove = worktree_sub.add_parser("remove", help="Remove a worktree and its branch")
    wt_remove.add_argument("slug", help="Worktree slug (e.g., feat+add-search)")
    wt_remove.add_argument("--force", action="store_true", help="Force removal of dirty worktree")
    wt_remove.set_defaults(func=_cmd_worktree)
    wt_status = worktree_sub.add_parser("status", help="Show current worktree context")
    wt_status.set_defaults(func=_cmd_worktree)

    # hook (nested subcommands for Claude Code and git hook dispatch)
    hook_parser = subparsers.add_parser("hook", help="Hook dispatch commands")
    hook_sub = hook_parser.add_subparsers(dest="hook_command", help="Hook subcommands")

    hs = hook_sub.add_parser("session-start", help="SessionStart hook")
    hs.set_defaults(func=_cmd_hook_session_start)

    he = hook_sub.add_parser("session-end", help="SessionEnd hook")
    he.set_defaults(func=_cmd_hook_session_end)

    hp = hook_sub.add_parser("pre-compact", help="PreCompact hook")
    hp.set_defaults(func=_cmd_hook_pre_compact)

    hf = hook_sub.add_parser("format-work", help="PostToolUse format hook")
    hf.add_argument("--edit", action="store_true", help="Edit mode (PostToolUse)")
    hf.set_defaults(func=_cmd_hook_format_work)

    hl = hook_sub.add_parser("lint-work", help="PostToolUse/PreToolUse lint hook")
    hl_grp = hl.add_mutually_exclusive_group()
    hl_grp.add_argument("--edit", action="store_true", help="Edit mode (PostToolUse)")
    hl_grp.add_argument("--commit", action="store_true", help="Commit mode (PreToolUse)")
    hl.set_defaults(func=_cmd_hook_lint_work)

    hv = hook_sub.add_parser("verify-commit", help="Verify commit messages")
    hv.add_argument("msg_file", nargs="?", help="Path to commit message file")
    hv.add_argument("--range", dest="range_spec", help="Git commit range")
    hv.add_argument("--message", help="Direct commit message text")
    hv.set_defaults(func=_cmd_hook_verify_commit)

    hc = hook_sub.add_parser("ci-check", help="Full local CI mirror")
    hc.add_argument("--fast", action="store_true", help="Skip slow checks")
    hc.add_argument("--commit-range", dest="commit_range", help="Git commit range")
    hc.set_defaults(func=_cmd_hook_ci_check)

    return parser


def main() -> None:
    """OCD umbrella command — dispatch subcommands."""
    parser = _build_parser()
    args = parser.parse_args()

    if args.command is None:
        _cmd_init(args)
        return

    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)

    args.func(args)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _is_valid_shell(shell: str) -> bool:
    """Check if a shell is in /etc/shells or is a known safe default."""
    safe_defaults = {
        "/bin/bash",
        "/bin/sh",
        "/bin/zsh",
        "/bin/fish",
        "/usr/bin/bash",
        "/usr/bin/zsh",
        "/usr/bin/fish",
    }
    if shell in safe_defaults:
        return True
    etc_shells = Path("/etc/shells")
    if etc_shells.exists():
        try:
            for line in etc_shells.read_text().splitlines():
                if line.strip() == shell:
                    return True
        except OSError:
            pass
    return False


def _detect_project(project_dir: Path) -> dict[str, bool]:
    """Detect what kind of project this is based on its contents."""
    return {
        "python": (project_dir / "pyproject.toml").exists(),
        "node": (project_dir / "package.json").exists(),
        "git": (project_dir / ".git").exists(),
    }


def _init_agent_dir(project_dir: Path) -> None:
    """Scaffold USER/ directory structure for the knowledge pipeline."""
    user_dir = project_dir / USER_DIR.relative_to(PROJECT_ROOT)
    gitignore = user_dir / ".gitignore"

    if gitignore.exists():
        return

    created = False
    for dir_path in USER_DIRS:
        full = project_dir / dir_path
        if not full.exists():
            full.mkdir(parents=True, exist_ok=True)
            created = True

    # Knowledge index
    local_knowledge_dir = project_dir / KNOWLEDGE_DIR.relative_to(PROJECT_ROOT)
    local_knowledge_dir.mkdir(parents=True, exist_ok=True)

    local_index_file = project_dir / INDEX_FILE.relative_to(PROJECT_ROOT)
    if not local_index_file.exists():
        local_index_file.write_text(DEFAULT_INDEX_CONTENT + "\n")
        created = True

    # .gitignore
    if not gitignore.exists():
        gitignore.write_text(USER_GITIGNORE)
        created = True

    if created:
        print(f"Created {USER_DIR.name}/ knowledge pipeline structure.")


def _init_vendor_dirs(project_dir: Path) -> None:
    """Scaffold vendor config directories for multi-tool support."""
    created = False
    for dir_path in VENDOR_DIRS:
        full = project_dir / dir_path
        if not full.exists():
            full.mkdir(parents=True, exist_ok=True)
            created = True
    if created:
        print("Created vendor config directories.")


def _copy_templates(project_dir: Path) -> list[str]:
    """Copy template assets from /opt/ocd/templates/ to the project directory.

    Never overwrites existing files. Returns list of items copied.
    Re-running ocd init after project changes will add any new templates
    without touching existing files.
    """
    if not TEMPLATES_DIR.is_dir():
        return []

    copied: list[str] = []

    for item in TEMPLATES_DIR.iterdir():
        dest = project_dir / item.name

        if item.is_dir():
            if dest.exists():
                # Merge: copy individual files that don't exist
                for sub in item.rglob("*"):
                    if sub.is_file():
                        rel = sub.relative_to(item)
                        sub_dest = dest / rel
                        if not sub_dest.exists():
                            sub_dest.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(sub, sub_dest)
                            copied.append(str(rel))
            else:
                shutil.copytree(item, dest)
                copied.append(f"{item.name}/")
        elif item.is_file() and not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest)
            copied.append(item.name)

    return copied


if __name__ == "__main__":
    main()
