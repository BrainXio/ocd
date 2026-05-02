"""OCD standards checkers — one callable per Nine Standard."""

__all__ = [
    "StandardsChecker",
    "Tool",
    "ToolResult",
    "ToolRunner",
    "check_consistent_defaults",
    "check_defense_in_depth",
    "check_deterministic_ordering",
    "check_inconsistent_elimination",
    "check_minimal_surface_area",
    "check_no_dead_code",
    "check_progressive_simplification",
    "check_single_source_of_truth",
    "check_structural_honesty",
    "ci_gate_tools",
    "fast_gate_tools",
]

from ocd.tools.runner import Tool, ToolResult, ToolRunner, ci_gate_tools, fast_gate_tools
from ocd.tools.standards_checker import (
    StandardsChecker,
    check_consistent_defaults,
    check_defense_in_depth,
    check_deterministic_ordering,
    check_inconsistent_elimination,
    check_minimal_surface_area,
    check_no_dead_code,
    check_progressive_simplification,
    check_single_source_of_truth,
    check_structural_honesty,
)
