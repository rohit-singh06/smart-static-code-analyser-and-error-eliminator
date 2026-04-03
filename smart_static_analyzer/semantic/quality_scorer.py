"""
Code Quality Scorer — evaluates code quality based on semantic analysis results.

Score: 100 − (15 × errors) − (5 × warnings)  [clamped to 0–100]
Grade: A(90+) B(75+) C(60+) D(45+) F(below 45)
"""
from __future__ import annotations
from typing import List


_GRADES = [
    (90, "A", "#3fb950", "Excellent — clean code with no detected issues."),
    (75, "B", "#58a6ff", "Good — minor issues detected."),
    (60, "C", "#e3b341", "Fair — several issues need attention."),
    (45, "D", "#ffa64d", "Poor — significant problems detected."),
    (0,  "F", "#f85149", "Critical — major semantic errors present."),
]


def compute_quality(issues: List) -> dict:
    """
    Compute a quality score from a list of SemanticIssue objects.
    Returns a dict suitable for JSON serialisation.
    """
    errors   = [i for i in issues if i.kind == "ERROR"]
    warnings = [i for i in issues if i.kind == "WARNING"]

    # Count specific warning types
    unreachable = sum(1 for i in warnings if i.code == "UNREACHABLE_CODE")
    unused      = sum(1 for i in warnings if i.code == "UNUSED_VAR")
    uninit      = sum(1 for i in warnings if i.code == "UNINITIALIZED_USE")

    score = 100 - len(errors) * 15 - len(warnings) * 5
    score = max(0, min(100, score))

    grade, color, summary = "F", "#f85149", "Critical"
    for threshold, g, c, s in _GRADES:
        if score >= threshold:
            grade, color, summary = g, c, s
            break

    return {
        "score": score,
        "grade": grade,
        "color": color,
        "summary": summary,
        "error_count":       len(errors),
        "warning_count":     len(warnings),
        "unreachable_count": unreachable,
        "unused_count":      unused,
        "uninit_count":      uninit,
        "breakdown": [
            {"label": "Semantic Errors",   "count": len(errors),   "points": len(errors) * 15},
            {"label": "Warnings",          "count": len(warnings), "points": len(warnings) * 5},
            {"label": "Unreachable Code",  "count": unreachable,   "points": 0},
            {"label": "Unused Variables",  "count": unused,        "points": 0},
            {"label": "Uninitialised Use", "count": uninit,        "points": 0},
        ],
    }
