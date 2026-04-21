"""OCD container initialization entry point."""

from __future__ import annotations

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
    KNOWLEDGE_DIR,
    PROJECT_ROOT,
    QA_DIR,
    REPORTS_DIR,
)
from ocd.format import run_formatters

TEMPLATES_DIR = Path("/opt/ocd/templates")

AGENT_DIRS = [
    str(p.relative_to(PROJECT_ROOT))
    for p in [DAILY_DIR, CONCEPTS_DIR, CONNECTIONS_DIR, QA_DIR, REPORTS_DIR]
]

AGENT_GITIGNORE = """\
# Ignore everything in .agent (runtime data)
*
# Except .gitkeep files (preserve directory structure)
!.gitkeep
# Except this .gitignore itself
!.gitignore
# And subdirectories (so git can traverse into them)
!*/
"""


def main() -> None:
    """OCD umbrella command — dispatch subcommands."""
    if len(sys.argv) < 2 or sys.argv[1] == "init":
        _init()
    elif sys.argv[1] == "shell":
        _shell()
    elif sys.argv[1] == "format":
        sys.exit(run_formatters())
    elif sys.argv[1] == "kb":
        _kb()
    elif sys.argv[1] == "route":
        _route()
    elif sys.argv[1] == "standards":
        _standards()
    elif sys.argv[1] in ("fix-cycle", "lint-and-fix", "test-and-fix", "security-scan-and-patch"):
        _fix()
    else:
        print(f"Unknown command: {sys.argv[1]}", file=sys.stderr)
        sys.exit(1)


def _kb() -> None:
    """Handle kb subcommands."""
    if len(sys.argv) < 3:
        print("Usage: ocd kb query --relevant-to <query>", file=sys.stderr)
        sys.exit(1)
    sub = sys.argv[2]
    if sub == "query":
        from ocd.relevance import main as relevance_main

        # Rebuild sys.argv for relevance CLI parsing
        kb_args = sys.argv[3:]
        sys.argv = [sys.argv[0], *kb_args]
        relevance_main()
    else:
        print(f"Unknown kb subcommand: {sub}", file=sys.stderr)
        sys.exit(1)


def _route() -> None:
    """Handle route subcommand — delegate to ocd.router."""
    from ocd.router import main as router_main

    route_args = sys.argv[2:]
    sys.argv = [sys.argv[0], *route_args]
    router_main()


def _standards() -> None:
    """Handle standards subcommand — delegate to ocd.standards."""
    from ocd.standards import main as standards_main

    standards_args = sys.argv[2:]
    sys.argv = [sys.argv[0], *standards_args]
    standards_main()


def _fix() -> None:
    """Handle fix subcommands — delegate to ocd.fix."""
    from ocd.fix import main as fix_main

    fix_args = sys.argv[1:]
    sys.argv = [sys.argv[0], *fix_args]
    fix_main()


def _shell() -> None:
    """Start an interactive shell with the OCD environment."""
    shell = os.environ.get("SHELL", "/bin/bash")
    if not _is_valid_shell(shell):
        shell = "/bin/bash"
    os.execvp(shell, [shell])  # nosemgrep: dangerous-os-exec-tainted-env-args


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
    """Scaffold .agent/ directory structure for the knowledge pipeline."""
    agent_dir = project_dir / ".agent"
    gitignore = agent_dir / ".gitignore"

    if gitignore.exists():
        return

    created = False
    for dir_path in AGENT_DIRS:
        full = project_dir / dir_path
        if not full.exists():
            full.mkdir(parents=True, exist_ok=True)
            (full / ".gitkeep").touch()
            created = True

    # Knowledge index
    local_knowledge_dir = project_dir / KNOWLEDGE_DIR.relative_to(PROJECT_ROOT)
    local_knowledge_dir.mkdir(parents=True, exist_ok=True)
    if not (local_knowledge_dir / ".gitkeep").exists():
        (local_knowledge_dir / ".gitkeep").touch()

    local_index_file = project_dir / INDEX_FILE.relative_to(PROJECT_ROOT)
    if not local_index_file.exists():
        local_index_file.write_text(DEFAULT_INDEX_CONTENT + "\n")
        created = True

    # .gitignore
    if not gitignore.exists():
        gitignore.write_text(AGENT_GITIGNORE)
        created = True

    if created:
        print("Created .agent/ knowledge pipeline structure.")


def _init() -> None:
    """Initialize the OCD environment in a container."""
    project_dir = Path.cwd()
    project = _detect_project(project_dir)

    # Scaffold .agent/ for knowledge pipeline
    _init_agent_dir(project_dir)

    # Seed templates from /opt/ocd/templates/
    copied = _copy_templates(project_dir)
    if copied:
        print("Seeded OCD templates:")
        for item in copied:
            print(f"  + {item}")
    elif TEMPLATES_DIR.is_dir():
        print("OCD templates already present, skipping.")

    # Python dependencies
    if project["python"]:
        print("→ Installing Python dependencies…")
        result = subprocess.run(["uv", "sync"], check=False)
        if result.returncode != 0:
            print(f"✗ uv sync failed (exit {result.returncode})", file=sys.stderr)
            sys.exit(result.returncode)

    # Node.js dependencies
    if project["node"]:
        print("→ Installing Node.js dependencies…")
        result = subprocess.run(["npm", "ci"], check=False)
        if result.returncode != 0:
            print(f"✗ npm ci failed (exit {result.returncode})", file=sys.stderr)
            sys.exit(result.returncode)

    # Git hooks
    hooks_script = project_dir / "git_hooks" / "setup-hooks.sh"
    if hooks_script.exists() and project["git"]:
        print("→ Installing git hooks…")
        result = subprocess.run(["bash", str(hooks_script)], check=False)
        if result.returncode != 0:
            print(f"✗ Git hooks failed (exit {result.returncode})", file=sys.stderr)
            sys.exit(result.returncode)

    print("OCD environment initialized.")


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
