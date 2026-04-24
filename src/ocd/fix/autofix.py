"""Autonomous self-corrective fix loops in isolated Git worktrees.

Wraps the existing fix.py closed-loop commands inside an iterative engine
that runs in worktrees under .claude/worktrees/. Iterates detect-fix-verify
until convergence or a max-iteration cap. Never modifies the main working
tree directly — all fixes happen in isolation and are merged only after
validation passes.

Usage:
    ocd autofix <target>                  # single-file fix-cycle loop
    ocd autofix <target> --batch          # lint-and-fix strategy
    ocd autofix <target> --max-iterations N
    ocd autofix <target> --dry-run        # report only, no merge
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from ocd.config import AUTOFIX_LOG, PROJECT_ROOT, WORKTREES_DIR
from ocd.fix.cycle import FixResult, fix_cycle, lint_and_fix

# ── Recursion guard ──────────────────────────────────────────────────────────

_GUARD_ENV = "OCD_AUTOFIX_RUNNING"

# ── Data structures ──────────────────────────────────────────────────────────

_BRANCH_MD_TEMPLATE = """\
---
branch: "{branch}"
intent: "{intent}"
created: "{created}"
strategy: "{strategy}"
max_iterations: {max_iterations}
---

Autofix worktree for: {intent}
Target: {target}
"""


@dataclass(frozen=True)
class WorktreeInfo:
    """Metadata for an OCD-managed worktree."""

    path: Path
    branch: str
    intent: str


@dataclass
class LoopResult:
    """Result from a self-corrective autofix loop."""

    result: FixResult = field(default_factory=FixResult)
    iterations: int = 0
    merged: bool = False

    def to_json(self) -> str:
        d = asdict(self)
        d["result"] = asdict(self.result)
        return json.dumps(d, indent=2)


# ── Worktree lifecycle ───────────────────────────────────────────────────────

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    """Convert text to a lowercase, hyphen-separated slug."""
    return _SLUG_RE.sub("-", text.lower()).strip("-")[:40]


def _now_ts() -> str:
    """Compact timestamp for branch names: YYYYMMDD-HHMMSS."""
    return datetime.now(UTC).astimezone().strftime("%Y%m%d-%H%M%S")


def _git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run a git command, returning the CompletedProcess."""
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=str(cwd or PROJECT_ROOT),
        timeout=30,
    )


def create_worktree(
    intent: str,
    *,
    target: str = "",
    strategy: str = "fix-cycle",
    max_iterations: int = 5,
) -> WorktreeInfo:
    """Create an isolated Git worktree under .claude/worktrees/.

    Generates a branch named autofix/<timestamp>-<slug>, checks out HEAD
    into a new directory, and writes a BRANCH.md intent file.
    """
    slug = _slugify(intent)
    ts = _now_ts()
    branch = f"autofix/{ts}-{slug}"
    worktree_path = WORKTREES_DIR / slug

    # Ensure the worktrees directory exists
    WORKTREES_DIR.mkdir(parents=True, exist_ok=True)

    result = _git("worktree", "add", "-b", branch, str(worktree_path), "HEAD")
    if result.returncode != 0:
        raise RuntimeError(f"git worktree add failed: {result.stderr.strip()}")

    # Write BRANCH.md
    branch_md = worktree_path / "BRANCH.md"
    branch_md.write_text(
        _BRANCH_MD_TEMPLATE.format(
            branch=branch,
            intent=intent,
            created=datetime.now(UTC).astimezone().isoformat(timespec="seconds"),
            strategy=strategy,
            max_iterations=max_iterations,
            target=target,
        )
    )

    return WorktreeInfo(path=worktree_path, branch=branch, intent=intent)


def remove_worktree(worktree: WorktreeInfo, *, force: bool = False) -> bool:
    """Remove a worktree and its branch."""
    force_flag = ["--force"] if force else []
    result = _git("worktree", "remove", *force_flag, str(worktree.path))
    if result.returncode != 0:
        return False

    _git("branch", "-D", worktree.branch)
    return True


def merge_worktree(worktree: WorktreeInfo) -> bool:
    """Merge the worktree branch into the current branch (main tree).

    Must be called from the main working tree, not from inside the worktree.
    """
    result = _git("merge", "--no-ff", worktree.branch, "-m", f"fix(autofix): {worktree.intent}")
    return result.returncode == 0


def list_worktrees() -> list[WorktreeInfo]:
    """List all OCD-managed worktrees by scanning for BRANCH.md files."""
    if not WORKTREES_DIR.is_dir():
        return []

    worktrees: list[WorktreeInfo] = []
    for entry in sorted(WORKTREES_DIR.iterdir()):
        branch_md = entry / "BRANCH.md"
        if not entry.is_dir() or not branch_md.exists():
            continue
        # Parse branch name from frontmatter
        text = branch_md.read_text()
        branch_match = re.search(r'^branch:\s*"(.+?)"', text, re.MULTILINE)
        intent_match = re.search(r'^intent:\s*"(.+?)"', text, re.MULTILINE)
        branch = branch_match.group(1) if branch_match else ""
        intent = intent_match.group(1) if intent_match else ""
        worktrees.append(WorktreeInfo(path=entry, branch=branch, intent=intent))

    return worktrees


# ── Self-corrective loop engine ──────────────────────────────────────────────


def _log_iteration(
    intent: str,
    branch: str,
    iteration: int,
    fix_result: FixResult,
    converged: bool,
    worktree_path: str,
    merged: bool,
) -> None:
    """Append one JSONL entry to the autofix audit log."""
    entry = {
        "timestamp": datetime.now(UTC).astimezone().isoformat(timespec="seconds"),
        "intent": intent,
        "branch": branch,
        "iteration": iteration,
        "fixed": fix_result.fixed,
        "remaining": fix_result.remaining,
        "converged": converged,
        "worktree_path": worktree_path,
        "merged": merged,
        "exit_code": fix_result.exit_code,
    }
    AUTOFIX_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUTOFIX_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _validate_worktree(worktree: WorktreeInfo) -> bool:
    """Run lightweight validation on the worktree before merging.

    Runs ruff check on files changed vs HEAD. Returns True if clean.
    """
    # Get list of changed files vs the parent branch
    diff = _git(
        "diff", "--name-only", "--diff-filter=ACM", "HEAD", worktree.branch, cwd=worktree.path
    )
    if diff.returncode != 0:
        return False

    changed = [f for f in diff.stdout.strip().splitlines() if f.endswith(".py")]
    if not changed:
        return True

    result = _git("worktree", "list")
    if result.returncode != 0:
        return False

    # Run ruff check on changed Python files inside the worktree
    ruff = subprocess.run(
        ["ruff", "check", *changed],
        capture_output=True,
        text=True,
        cwd=str(worktree.path),
        timeout=15,
    )
    return ruff.returncode == 0


def autofix_loop(
    target: str,
    intent: str,
    *,
    max_iterations: int = 5,
    strategy: str = "fix-cycle",
    dry_run: bool = False,
) -> LoopResult:
    """Run a self-corrective fix loop in an isolated worktree.

    Creates a worktree, iterates detect-fix-verify until convergence or
    max_iterations, validates the result, and optionally merges.
    """
    loop_result = LoopResult()
    worktree = create_worktree(
        intent, target=target, strategy=strategy, max_iterations=max_iterations
    )

    prev_remaining: list[str] | None = None

    for i in range(max_iterations):
        # Run the appropriate fix strategy inside the worktree
        if strategy == "lint-and-fix":
            fix_result = lint_and_fix(target, project_root=worktree.path)
        else:
            fix_result = fix_cycle(target, project_root=worktree.path)

        loop_result.result.fixed.extend(fix_result.fixed)
        loop_result.result.remaining = fix_result.remaining
        loop_result.iterations = i + 1

        converged = len(fix_result.remaining) == 0

        # Check for no-progress (identical remaining list)
        if (
            not converged
            and prev_remaining is not None
            and sorted(fix_result.remaining) == sorted(prev_remaining)
        ):
            _log_iteration(
                intent,
                worktree.branch,
                i + 1,
                fix_result,
                False,
                str(worktree.path.relative_to(PROJECT_ROOT)),
                False,
            )
            break

        _log_iteration(
            intent,
            worktree.branch,
            i + 1,
            fix_result,
            converged,
            str(worktree.path.relative_to(PROJECT_ROOT)),
            False,
        )

        if converged:
            break

        prev_remaining = list(fix_result.remaining)

    # Post-loop: validate and optionally merge
    if not dry_run and len(loop_result.result.remaining) == 0:
        validation_ok = _validate_worktree(worktree)
        if validation_ok:
            merged = merge_worktree(worktree)
            if merged:
                remove_worktree(worktree)
                loop_result.merged = True
                loop_result.result.exit_code = 0
            else:
                loop_result.result.remaining.append(
                    "merge conflict — worktree preserved for review"
                )
                loop_result.result.exit_code = 1
        else:
            loop_result.result.remaining.append("validation failed — worktree preserved for review")
            loop_result.result.exit_code = 1

    if dry_run:
        remove_worktree(worktree, force=True)

    if not loop_result.merged and not dry_run:
        loop_result.result.exit_code = 1 if loop_result.result.remaining else 0

    return loop_result


# ── CLI entry point ──────────────────────────────────────────────────────────


def main() -> None:
    """Entry point for ocd autofix command."""
    # Recursion guard
    if os.environ.get(_GUARD_ENV):
        return

    parser = argparse.ArgumentParser(
        prog="ocd-autofix",
        description="Self-corrective fix loop in isolated worktree",
    )
    parser.add_argument("target", help="File or directory path to fix")
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Use lint-and-fix strategy instead of fix-cycle",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=5,
        help="Max loop iterations (default: 5)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report findings only, no merge",
    )

    args = parser.parse_args()

    strategy = "lint-and-fix" if args.batch else "fix-cycle"
    intent = _slugify(args.target) or "autofix"

    os.environ[_GUARD_ENV] = "1"
    try:
        result = autofix_loop(
            args.target,
            intent,
            max_iterations=args.max_iterations,
            strategy=strategy,
            dry_run=args.dry_run,
        )
        print(result.to_json())
        sys.exit(result.result.exit_code)
    finally:
        os.environ.pop(_GUARD_ENV, None)


if __name__ == "__main__":
    main()
