"""
AST parsing via pycparser (C grammar subset, no preprocessing).

pycparser does not run the C preprocessor, so we strip preprocessor lines
that start with '#', e.g. #include, #define, etc.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


def strip_preprocessor_lines(code: str) -> str:
    """Remove lines starting with '#' to avoid preprocessor directives."""
    out_lines: list[str] = []
    for line in code.splitlines():
        if line.lstrip().startswith("#"):
            continue
        out_lines.append(line)
    return "\n".join(out_lines) + ("\n" if code.endswith("\n") else "")


@dataclass
class PycparserResult:
    ok: bool
    error: Optional[str]
    ast: Optional[dict]

    def to_dict(self) -> dict:
        return {"ok": self.ok, "error": self.error, "ast": self.ast}


def _node_to_dict(node: Any) -> Any:
    """
    Convert pycparser AST nodes into a JSON-serializable structure.
    Keeps it lightweight: node type + important scalar attrs + children.
    """
    if node is None:
        return None
    # pycparser nodes have a class name and children() iterator
    cls_name = node.__class__.__name__
    result: dict[str, Any] = {"type": cls_name}

    # capture some common simple attributes if present
    for attr in ("name", "op", "value", "type"):
        if hasattr(node, attr):
            v = getattr(node, attr)
            if isinstance(v, (str, int, float, bool)) or v is None:
                result[attr] = v

    children_list = []
    try:
        for (child_name, child) in node.children():
            children_list.append({"field": child_name, "node": _node_to_dict(child)})
    except Exception:
        children_list = []
    result["children"] = children_list
    return result


def parse_with_pycparser(code: str) -> PycparserResult:
    """Parse code into pycparser AST (after stripping preprocessor lines)."""
    try:
        from pycparser import c_parser
    except Exception as e:
        return PycparserResult(
            ok=False,
            error="pycparser is not installed. Run: pip install pycparser",
            ast=None,
        )

    cleaned = strip_preprocessor_lines(code)
    try:
        parser = c_parser.CParser()
        ast = parser.parse(cleaned)
        return PycparserResult(ok=True, error=None, ast=_node_to_dict(ast))
    except Exception as e:
        return PycparserResult(ok=False, error=str(e), ast=None)

