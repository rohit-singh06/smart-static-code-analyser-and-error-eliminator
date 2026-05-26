"""
AST parsing via pycparser for subset C grammar (ignoring preprocessor lines starting with '#').
"""

class PycparserResult:
    def __init__(self, ok: bool, error: str | None, ast: dict | None):
        self.ok = ok
        self.error = error
        self.ast = ast

    def to_dict(self) -> dict:
        return self.__dict__


def strip_preprocessor_lines(code: str) -> str:
    """Filter out preprocessor directive lines starting with '#'."""
    lines = [line for line in code.splitlines() if not line.lstrip().startswith("#")]
    return "\n".join(lines) + ("\n" if code.endswith("\n") else "")


def _node_to_dict(node) -> dict | None:
    """Convert pycparser AST node recursively to serializable dictionary."""
    if node is None:
        return None

    res = {"type": node.__class__.__name__}
    for attr in ("name", "op", "value", "type"):
        if hasattr(node, attr):
            val = getattr(node, attr)
            if isinstance(val, (str, int, float, bool)) or val is None:
                res[attr] = val

    children = []
    try:
        for name, child in node.children():
            children.append({"field": name, "node": _node_to_dict(child)})
    except Exception:
        pass
    res["children"] = children
    return res


def parse_with_pycparser(code: str) -> PycparserResult:
    """Parse code with pycparser parser."""
    try:
        from pycparser import c_parser
    except Exception:
        return PycparserResult(False, "pycparser is not installed. Run: pip install pycparser", None)

    cleaned = strip_preprocessor_lines(code)
    try:
        parser = c_parser.CParser()
        ast = parser.parse(cleaned)
        return PycparserResult(True, None, _node_to_dict(ast))
    except Exception as e:
        return PycparserResult(False, str(e), None)
