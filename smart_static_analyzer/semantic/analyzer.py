"""
Semantic Analyzer — walks the AST and detects semantic/logical issues.
Checks: UNDECLARED_VAR, REDECLARATION, UNUSED_VAR, UNINITIALIZED_USE, UNREACHABLE_CODE, TYPE_MISMATCH.
"""

from typing import List
from semantic.symbol_table import SymbolTable, Symbol

HINTS = {
    "UNDECLARED_VAR": "Declare '{var}' before using it, e.g. `int {var};`",
    "REDECLARATION": "Remove the duplicate declaration or rename '{var}'.",
    "UNUSED_VAR": "Either use '{var}' somewhere or remove its declaration.",
    "UNINITIALIZED_USE": "Assign a value to '{var}' before using it, e.g. `{var} = 0;`",
    "UNREACHABLE_CODE": "Move or remove statements that appear after a return.",
    "TYPE_MISMATCH": "Check the type of '{var}' and the value being assigned to it.",
}

# Type systems promotion and rules
TYPE_ORDER = ["char", "short", "int", "long", "float", "double"]

WIDENING = {
    "char": {"char"},
    "short": {"short", "char"},
    "int": {"int", "short", "char"},
    "long": {"long", "int", "short", "char"},
    "float": {"float", "long", "int", "short", "char"},
    "double": {"double", "float", "long", "int", "short", "char"},
}

NARROWING = {
    "int": {"float", "double"},
    "short": {"int", "long", "float", "double"},
    "char": {"short", "int", "long", "float", "double"},
    "long": {"double"},
}


class SemanticIssue:
    def __init__(self, kind: str, code: str, message: str, line: int, variable: str | None = None, declared_line: int | None = None):
        self.kind = kind
        self.code = code
        self.message = message
        self.line = line
        self.variable = variable
        self.declared_line = declared_line

    def hint(self) -> str:
        return HINTS.get(self.code, "").replace("{var}", self.variable or "x")

    def to_dict(self) -> dict:
        qf = None
        target_line = self.declared_line if self.declared_line is not None else self.line
        if self.code == "UNINITIALIZED_USE" and self.variable:
            qf = {
                "label": f"Initialize '{self.variable}' to 0",
                "action": "initialize_zero",
                "line": target_line,
                "variable": self.variable
            }
        elif self.code == "UNUSED_VAR" and self.variable:
            qf = {
                "label": f"Remove unused '{self.variable}'",
                "action": "remove_declaration",
                "line": target_line,
                "variable": self.variable
            }
        elif self.code == "UNREACHABLE_CODE":
            qf = {
                "label": "Remove unreachable statement",
                "action": "remove_line",
                "line": self.line
            }

        return {
            "kind": self.kind,
            "code": self.code,
            "message": self.message,
            "line": self.line,
            "variable": self.variable,
            "hint": self.hint(),
            "quick_fix": qf,
        }


class SemanticResult:
    def __init__(self, issues: List[SemanticIssue] = None, symbol_table: SymbolTable = None):
        self.issues = issues or []
        self.symbol_table = symbol_table

    @property
    def errors(self) -> List[SemanticIssue]:
        return [i for i in self.issues if i.kind == "ERROR"]

    @property
    def warnings(self) -> List[SemanticIssue]:
        return [i for i in self.issues if i.kind == "WARNING"]

    def to_dict(self) -> dict:
        return {
            "issues": [i.to_dict() for i in self.issues],
            "symbol_table": self.symbol_table.to_list() if self.symbol_table else [],
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }


class SemanticAnalyzer:
    def __init__(self):
        self.symbol_table = SymbolTable()
        self.issues = []

    def analyze(self, ast_root) -> SemanticResult:
        self.visit(ast_root)
        # Check global scope for unused variables at the end
        self._check_unused(self.symbol_table.scopes[0])
        return SemanticResult(issues=self.issues, symbol_table=self.symbol_table)

    def visit(self, node) -> None:
        if node is None:
            return
        # Dispatch dynamically to visit_node_type or fallback to default children visitor
        handler_name = f"visit_{node.type.lower()}"
        handler = getattr(self, handler_name, self.visit_children)
        handler(node)

    def visit_children(self, node) -> None:
        for child in node.children:
            self.visit(child)

    def visit_program(self, node) -> None:
        self.visit_children(node)

    def visit_functiondef(self, node) -> None:
        name = node.value or ""
        line = node.line
        res = self.symbol_table.declare(name, "function", line)
        if res == "REDECLARATION":
            self._report_error("REDECLARATION", f"Function '{name}' is already declared.", line, name)
        else:
            self.symbol_table.mark_assigned(name, line)

        self.symbol_table.enter_scope()
        for child in node.children:  # Function body is block
            self._visit_block_stmts(child)
        scope = self.symbol_table.exit_scope()
        self._check_unused(scope)

    def visit_block(self, node) -> None:
        self.symbol_table.enter_scope()
        self._visit_block_stmts(node)
        scope = self.symbol_table.exit_scope()
        self._check_unused(scope)

    def _visit_block_stmts(self, node) -> None:
        return_seen = False
        for stmt in node.children:
            if return_seen:
                self._report_warning("UNREACHABLE_CODE", "Statement is unreachable (follows a return).", stmt.line)
                break
            self.visit(stmt)
            if stmt.type == "Return":
                return_seen = True

    def visit_declaration(self, node) -> None:
        name = node.value
        line = node.line
        var_type = node.meta.get("var_type", "int")
        res = self.symbol_table.declare(name, var_type, line)
        if res == "REDECLARATION":
            self._report_error("REDECLARATION", f"Variable '{name}' is already declared in this scope.", line, name)

        if node.children:
            initializer = node.children[0]
            self.visit(initializer)
            self.symbol_table.mark_assigned(name, line)
            inferred = self._infer_type(initializer)
            self._check_type_compatibility(var_type, inferred, line, name)

    def visit_assignment(self, node) -> None:
        if len(node.children) < 1:
            return
        lhs = node.children[0]
        name = lhs.value
        line = lhs.line or node.line

        sym = self.symbol_table.lookup(name)
        if sym is None:
            self._report_error("UNDECLARED_VAR", f"Variable '{name}' is assigned but was never declared.", line, name)
        else:
            self.symbol_table.mark_assigned(name, line)

        if len(node.children) >= 2:
            rhs = node.children[1]
            self.visit(rhs)
            if sym is not None:
                target_type = sym.type_
                if lhs.meta.get("is_subscripted") and target_type.endswith("[]"):
                    target_type = target_type[:-2]
                inferred = self._infer_type(rhs)
                self._check_type_compatibility(target_type, inferred, line, name)

    def visit_return(self, node) -> None:
        self.visit_children(node)

    def visit_identifier(self, node) -> None:
        name = node.value
        line = node.line
        sym = self.symbol_table.lookup(name)
        if sym is None:
            self._report_error("UNDECLARED_VAR", f"Variable '{name}' is used but was never declared.", line, name)
        else:
            if not sym.assigned and sym.type_ not in ("function", "builtin"):
                self._report_warning("UNINITIALIZED_USE", f"Variable '{name}' may be used before being assigned a value.", line, name, sym.declared_line)
            self.symbol_table.mark_used(name, line)

    def visit_expressionstatement(self, node) -> None:
        self.visit_children(node)

    def visit_callexpression(self, node) -> None:
        callee = node.value or ""
        line = node.line
        sym = self.symbol_table.lookup(callee)
        if sym is None:
            self._report_warning("UNDECLARED_VAR", f"Function '{callee}' is called but not declared.", line, callee)
        else:
            self.symbol_table.mark_used(callee, line)
        for arg in node.children:
            self.visit(arg)

    def visit_binaryop(self, node) -> None:
        self.visit_children(node)

    def visit_number(self, node) -> None:
        pass

    def visit_string(self, node) -> None:
        pass

    # Type Helpers
    def _infer_type(self, node) -> str:
        if node is None:
            return "unknown"
        t = node.type
        if t == "Number":
            return "float" if isinstance(node.value, float) else "int"
        if t == "String":
            return node.meta.get("literal_type", "string")
        if t == "Identifier":
            sym = self.symbol_table.lookup(node.value)
            return sym.type_ if sym else "unknown"
        if t == "BinaryOp":
            types = [self._infer_type(c) for c in node.children]
            return self._wider_type(types)
        return "unknown"

    def _wider_type(self, types: list) -> str:
        widest_idx = -1
        widest = "int"
        for t in types:
            if t in TYPE_ORDER:
                idx = TYPE_ORDER.index(t)
                if idx > widest_idx:
                    widest_idx = idx
                    widest = t
        return widest

    def _check_type_compatibility(self, target: str, source: str, line: int, var: str) -> None:
        if "unknown" in (source, target) or "void" in (source, target):
            return
        t_base = target.rstrip("*[]").strip()
        s_base = source.rstrip("*[]").strip()
        if t_base == s_base:
            return

        if s_base == "string" and "*" not in target and "[]" not in target:
            self._report_error("TYPE_MISMATCH", f"Cannot assign a string literal to '{var}' of type '{target}'.", line, var)
            return

        if t_base in WIDENING and s_base in WIDENING.get(t_base, set()):
            return

        if t_base in NARROWING and s_base in NARROWING.get(t_base, set()):
            self._report_warning(
                "TYPE_MISMATCH",
                f"Possible data loss: assigning '{source}' value to '{var}' of type '{target}' (narrowing conversion).",
                line, var
            )
            return

        self._report_warning("TYPE_MISMATCH", f"Type mismatch: '{var}' is '{target}' but expression evaluates to '{source}'.", line, var)

    def _report_error(self, code: str, msg: str, line: int, var: str = None) -> None:
        self.issues.append(SemanticIssue("ERROR", code, msg, line, var))

    def _report_warning(self, code: str, msg: str, line: int, var: str = None, declared_line: int = None) -> None:
        # Avoid duplicate warnings
        for issue in self.issues:
            if issue.code == code and issue.variable == var and issue.line == line:
                return
        self.issues.append(SemanticIssue("WARNING", code, msg, line, var, declared_line))

    def _check_unused(self, scope: dict) -> None:
        for sym in scope.values():
            if sym.type_ in ("builtin", "function"):
                continue
            if not sym.used:
                self._report_warning("UNUSED_VAR", f"Variable '{sym.name}' is declared but never used.", sym.declared_line, sym.name)
