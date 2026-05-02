"""ToolRunner — registry and executor for external tool invocations.

Abstracts the direct knowledge of gitleaks, ruff, mypy, etc. command lines
from ocd_check and ocd_ci_check into a data-driven registry.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Tool:
    """Describes an external tool that OCD can invoke.

    Attributes:
        name: Human-readable name for the check result (e.g. "ruff-check").
        binary: The command binary to look up on PATH.
        args: Positional arguments to pass after the binary.
        timeout: Maximum seconds before killing the process.
        cwd_suffix: If set, append this to the project root as cwd.
        config_flag: If set, look for this config file and pass it via this flag.
    """

    name: str
    binary: str
    args: list[str] = field(default_factory=list)
    timeout: int = 30
    cwd_suffix: str | None = None
    config_flag: tuple[str, str] | None = None

    def is_available(self) -> bool:
        """Check if the binary is available on PATH."""
        return shutil.which(self.binary) is not None

    def build_command(self, root: Path) -> list[str]:
        """Build the full command list, including config flags if present."""
        cmd = [self.binary, *self.args]
        if self.config_flag:
            flag, filename = self.config_flag
            config_path = root / filename
            if config_path.exists():
                cmd.extend([flag, str(config_path)])
        return cmd


@dataclass
class ToolResult:
    """Result of running a single tool check."""

    check: str
    status: str
    detail: str


class ToolRunner:
    """Registry-driven tool executor for quality gates.

    Register tools with :meth:`register`, then call :meth:`run_all`
    or :meth:`run_one` to execute them. Tools that are not installed
    are automatically skipped with status ``"skip"``.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self._tools: list[Tool] = []

    def register(self, tool: Tool) -> None:
        """Add a tool to the registry."""
        self._tools.append(tool)

    def run_one(self, tool: Tool) -> ToolResult:
        """Run a single tool and return a structured result."""
        if not tool.is_available():
            return ToolResult(
                check=tool.name,
                status="skip",
                detail=f"{tool.binary} not installed",
            )

        cmd = tool.build_command(self.root)
        cwd = self.root / tool.cwd_suffix if tool.cwd_suffix else self.root
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=tool.timeout,
                cwd=str(cwd),
            )
            output = (result.stderr + result.stdout).strip()
            ok = result.returncode == 0
        except subprocess.TimeoutExpired:
            return ToolResult(
                check=tool.name,
                status="fail",
                detail=f"timed out after {tool.timeout}s",
            )
        except FileNotFoundError:
            return ToolResult(
                check=tool.name,
                status="skip",
                detail=f"{tool.binary} not installed",
            )

        return ToolResult(
            check=tool.name,
            status="pass" if ok else "fail",
            detail="clean" if ok else output,
        )

    def run_all(self) -> list[ToolResult]:
        """Run all registered tools and return results."""
        return [self.run_one(tool) for tool in self._tools]

    def results_as_dicts(self, results: list[ToolResult]) -> list[dict[str, str]]:
        """Convert results to plain dicts for JSON serialization."""
        return [{"check": r.check, "status": r.status, "detail": r.detail} for r in results]


def fast_gate_tools(root: Path) -> list[Tool]:
    """Return the tool definitions for the fast quality gate (ocd_check)."""
    return [
        Tool(
            name="secret-scan",
            binary="gitleaks",
            args=["protect", "--staged"],
            timeout=30,
            config_flag=("-c", ".gitleaks.toml"),
        ),
        Tool(
            name="ruff-check",
            binary="ruff",
            args=["check", "src/", "tests/"],
            timeout=30,
        ),
    ]


def ci_gate_tools(root: Path, fast: bool = False) -> list[Tool]:
    """Return the tool definitions for the full CI gate (ocd_ci_check)."""
    tools: list[Tool] = [
        Tool(
            name="secret-scan",
            binary="gitleaks",
            args=["detect", "--source", "."],
            timeout=60,
            config_flag=("-c", ".gitleaks.toml"),
        ),
        Tool(
            name="ruff-check",
            binary="ruff",
            args=["check", "src/", "tests/"],
            timeout=30,
        ),
        Tool(
            name="ruff-format",
            binary="ruff",
            args=["format", "--check", "src/", "tests/"],
            timeout=30,
        ),
        Tool(
            name="mypy",
            binary="mypy",
            args=["src/ocd/", "--strict"],
            timeout=60,
        ),
        Tool(
            name="yamllint",
            binary="yamllint",
            args=["-f", "parsable", ".github/workflows/", ".yamllint"],
            timeout=15,
        ),
    ]
    return tools
