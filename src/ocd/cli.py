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
    KNOWLEDGE_DIR,
    OCD_DB,
    PROJECT_ROOT,
    QA_DIR,
    REPORTS_DIR,
    STATE_DIR,
    USER_DIR,
)
from ocd.format import run_formatters

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
        REPORTS_DIR,
        STATE_DIR,
        USER_DIR / "logs",
        USER_DIR / "agents" / "tasks",
        USER_DIR / "agents" / "runtime",
        USER_DIR / "cache",
        KNOWLEDGE_DIR / "raw",
        KNOWLEDGE_DIR / "archive",
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

    hooks_script = project_dir / "git_hooks" / "setup-hooks.sh"
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
        from ocd.relevance import (
            build_kb_index_json,
            score_articles,
        )

        index = build_kb_index_json(use_db=True)
        if args.vectors:
            from ocd.relevance import hybrid_score_articles

            scored = hybrid_score_articles(
                args.relevant_to, index, db_path=OCD_DB, top_k=args.top_k or KB_INJECTION_COUNT
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
    from ocd.router import main as router_main

    argv = ["ocd-route"]
    if args.build_manifest:
        argv.append("--build-manifest")
    if args.max != 3:
        argv.extend(["--max", str(args.max)])
    argv.extend(args.query)
    sys.argv = argv
    router_main()


def _cmd_standards(args: argparse.Namespace) -> None:
    """Manage standards hash reference."""
    from ocd.standards import main as standards_main

    argv = ["ocd-standards"]
    if args.verify:
        argv.append("--verify")
    if args.update:
        argv.append("--update")
    sys.argv = argv
    standards_main()


def _cmd_fix(args: argparse.Namespace) -> None:
    """Closed-loop fix commands."""
    from ocd.fix import fix_cycle, lint_and_fix, security_scan_and_patch, test_and_fix

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
    from ocd.check import run_check

    sys.exit(run_check())


def _cmd_ci_check(args: argparse.Namespace) -> None:
    """Full local CI mirror."""
    from ocd.ci_check import main as ci_check_main

    argv = ["ocd-ci-check"]
    if args.fast:
        argv.append("--fast")
    if args.commit_range:
        argv.extend(["--commit-range", args.commit_range])
    sys.argv = argv
    ci_check_main()


def _cmd_verify_commit(args: argparse.Namespace) -> None:
    """Verify commit messages."""
    from ocd.verify_commit import main as verify_commit_main

    argv = ["ocd-verify-commit"]
    if args.msg_file:
        argv.append(args.msg_file)
    if args.range_spec:
        argv.extend(["--range", args.range_spec])
    if args.message:
        argv.extend(["--message", args.message])
    sys.argv = argv
    verify_commit_main()


def _cmd_scan_secrets(args: argparse.Namespace) -> None:
    """Scan for secrets in source code."""
    from ocd.scan_secrets import main as scan_secrets_main

    argv = ["ocd-scan-secrets"]
    if args.staged:
        argv.append("--staged")
    if args.source:
        argv.extend(["--source", args.source])
    sys.argv = argv
    scan_secrets_main()


def _cmd_materialize(args: argparse.Namespace) -> None:
    """Materialize .claude/ content from database to target directory."""
    from ocd.materialize import main as materialize_main

    argv = ["ocd-materialize"]
    if args.target:
        argv.extend(["--target", args.target])
    if args.db:
        argv.extend(["--db", args.db])
    if args.force:
        argv.append("--force")
    if args.vendor:
        argv.extend(["--vendor", args.vendor])
    sys.argv = argv
    materialize_main()


def _cmd_compile(args: argparse.Namespace) -> None:
    """Compile daily logs into knowledge articles."""
    from ocd.compile import main as compile_main

    argv = ["ocd-compile"]
    if args.all:
        argv.append("--all")
    if args.file:
        argv.extend(["--file", args.file])
    if args.dry_run:
        argv.append("--dry-run")
    if args.manifest:
        argv.append("--manifest")
    if args.update_standards_hash:
        argv.append("--update-standards-hash")
    sys.argv = argv
    compile_main()


def _cmd_ingest(args: argparse.Namespace) -> None:
    """Ingest raw knowledge articles into ocd.db."""
    from ocd.ingest import ingest_raw

    result = ingest_raw(force_all=args.all, dry_run=args.dry_run)
    print(result.to_json())
    sys.exit(1 if result.errors else 0)


def _cmd_vec(args: argparse.Namespace) -> None:
    """Handle vec subcommands."""
    from ocd.vec import main as vec_main

    argv = ["ocd-vec"]
    if args.vec_command == "rebuild":
        argv.append("rebuild")
        if args.force:
            argv.append("--force")
    elif args.vec_command == "search":
        argv.append("search")
        argv.append(args.query)
        if args.top_k:
            argv.extend(["--top-k", str(args.top_k)])
    elif args.vec_command == "status":
        argv.append("status")
    sys.argv = argv
    vec_main()


def _cmd_flush(args: argparse.Namespace) -> None:
    """Flush conversation context to daily log."""
    from ocd.flush import main as flush_main

    argv = ["ocd-flush"]
    if args.context_file:
        argv.append(args.context_file)
    if args.session_id:
        argv.append(args.session_id)
    sys.argv = argv
    flush_main()


def _cmd_query(args: argparse.Namespace) -> None:
    """Query the personal knowledge base."""
    from ocd.query import main as query_main

    argv = ["ocd-query", args.question]
    if args.file_back:
        argv.append("--file-back")
    sys.argv = argv
    query_main()


def _cmd_lint_kb(args: argparse.Namespace) -> None:
    """Lint the knowledge base for structural issues."""
    from ocd.lint import main as lint_main

    argv = ["ocd-lint-kb"]
    if args.structural_only:
        argv.append("--structural-only")
    sys.argv = argv
    sys.exit(lint_main())


def _cmd_compile_db(args: argparse.Namespace) -> None:
    """Compile .claude/ content into bundled SQLite database."""
    from ocd.pack import main as pack_main

    argv = ["ocd-compile-db"]
    if args.output:
        argv.extend(["--output", args.output])
    if args.source:
        argv.extend(["--source", args.source])
    sys.argv = argv
    pack_main()


def _cmd_pre_push(args: argparse.Namespace) -> None:
    """Diff-aware pre-push test runner."""
    from ocd.pre_push import main as pre_push_main

    sys.argv = ["ocd-pre-push"]
    pre_push_main()


def _cmd_autofix(args: argparse.Namespace) -> None:
    """Self-corrective fix loop in isolated worktree."""
    from ocd.autofix import main as autofix_main

    argv = ["ocd-autofix"]
    if args.target:
        argv.append(args.target)
    if args.batch:
        argv.append("--batch")
    if args.max_iterations:
        argv.extend(["--max-iterations", str(args.max_iterations)])
    if args.dry_run:
        argv.append("--dry-run")
    sys.argv = argv
    autofix_main()


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
    from ocd.hooks.format_work import main as format_work_main

    argv = ["ocd-format-work"]
    if args.edit:
        argv.append("--edit")
    sys.argv = argv
    format_work_main()


def _cmd_hook_lint_work(args: argparse.Namespace) -> None:
    """PostToolUse/PreToolUse lint hook."""
    from ocd.hooks.lint_work import main as lint_work_main

    argv = ["ocd-lint-work"]
    if args.edit:
        argv.append("--edit")
    elif args.commit:
        argv.append("--commit")
    sys.argv = argv
    lint_work_main()


def _cmd_hook_verify_commit(args: argparse.Namespace) -> None:
    """Verify commit messages for AI attribution patterns."""
    from ocd.verify_commit import main as verify_commit_main

    argv = ["ocd-verify-commit"]
    if args.msg_file:
        argv.append(args.msg_file)
    if args.range_spec:
        argv.extend(["--range", args.range_spec])
    if args.message:
        argv.extend(["--message", args.message])
    sys.argv = argv
    verify_commit_main()


def _cmd_hook_ci_check(args: argparse.Namespace) -> None:
    """Full local CI mirror."""
    from ocd.ci_check import main as ci_check_main

    argv = ["ocd-ci-check"]
    if args.fast:
        argv.append("--fast")
    if args.commit_range:
        argv.extend(["--commit-range", args.commit_range])
    sys.argv = argv
    ci_check_main()


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
        help="Vendor format (aider, cursor, copilot, windsurf, amazonq, all, agents-md)",
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

    # ingest
    ingest_parser = subparsers.add_parser(
        "ingest", help="Ingest raw knowledge articles into ocd.db"
    )
    ingest_parser.add_argument("--all", action="store_true", help="Force re-ingest all files")
    ingest_parser.add_argument("--dry-run", action="store_true", help="Report only, no DB changes")
    ingest_parser.set_defaults(func=_cmd_ingest)

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
    cdb_parser = subparsers.add_parser("compile-db", help="Compile .claude/ into SQLite database")
    cdb_parser.add_argument("--output", "-o", default=None, help="Output database path")
    cdb_parser.add_argument("--source", default=None, help="Source directory")
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
        "git": (project_dir / ".git").is_dir(),
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
