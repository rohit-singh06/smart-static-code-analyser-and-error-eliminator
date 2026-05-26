"""
Code Quality Scorer — evaluates code based on semantic analysis issues.
"""

from typing import List

GRADES = [
    (90, "A", "#3fb950", "Excellent — clean code with no detected issues."),
    (75, "B", "#58a6ff", "Good — minor issues detected."),
    (60, "C", "#e3b341", "Fair — several issues need attention."),
    (45, "D", "#ffa64d", "Poor — significant problems detected."),
    (0,  "F", "#f85149", "Critical — major semantic errors present."),
]


def compute_quality(issues: List) -> dict:
    """Compute quality score and grading details from a list of SemanticIssues."""
    errors = [i for i in issues if i.kind == "ERROR"]
    warnings = [i for i in issues if i.kind == "WARNING"]

    # Count specific kinds of warning issues
    unreachable = sum(1 for i in warnings if i.code == "UNREACHABLE_CODE")
    unused = sum(1 for i in warnings if i.code == "UNUSED_VAR")
    uninit = sum(1 for i in warnings if i.code == "UNINITIALIZED_USE")
    inf_loop = sum(1 for i in warnings if i.code == "INFINITE_LOOP")
    type_errors = sum(1 for i in errors if i.code == "TYPE_MISMATCH")
    type_warns = sum(1 for i in warnings if i.code == "TYPE_MISMATCH")

    hard_errors = len(errors) - type_errors

    # Deduction system
    score = 100 - (hard_errors * 15) - (type_errors * 10) - (len(warnings) * 5)
    score = max(0, min(100, score))

    # Evaluate Grade
    grade, color, summary = "F", "#f85149", "Critical"
    for threshold, g, c, s in GRADES:
        if score >= threshold:
            grade, color, summary = g, c, s
            break

    return {
        "score": score,
        "grade": grade,
        "color": color,
        "summary": summary,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "unreachable_count": unreachable,
        "unused_count": unused,
        "uninit_count": uninit,
        "infinite_loop_count": inf_loop,
        "type_mismatch_count": type_errors + type_warns,
        "breakdown": [
            {"label": "Semantic Errors", "count": hard_errors, "points": hard_errors * 15},
            {"label": "Type Mismatches", "count": type_errors + type_warns, "points": type_errors * 10 + type_warns * 5},
            {"label": "Warnings", "count": len(warnings) - type_warns, "points": (len(warnings) - type_warns) * 5},
            {"label": "Infinite Loops", "count": inf_loop, "points": 0},
            {"label": "Unreachable Code", "count": unreachable, "points": 0},
            {"label": "Unused Variables", "count": unused, "points": 0},
            {"label": "Uninitialised Use", "count": uninit, "points": 0},
        ],
    }
