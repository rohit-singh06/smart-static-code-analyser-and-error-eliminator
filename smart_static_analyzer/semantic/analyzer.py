"""
Semantic Analyzer — walks the AST and detects semantic/logical errors.

Checks performed:
  ERROR   UNDECLARED_VAR    — identifier used without being declared
  ERROR   REDECLARATION     — variable declared twice in the same scope
  WARNING UNUSED_VAR        — variable declared but never read
  WARNING UNINITIALIZED_USE — variable read before any assignment
  WARNING UNREACHABLE_CODE  — statements after a return in the same block
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List

try:
    from .symbol_table import SymbolTable, Symbol
except ImportError:
    from symbol_table import SymbolTable, Symbol

# ── Issue model ──────────────────────────────────────────────────────────────

_HINTS = {
    "UNDECLARED_VAR":    "Declare '{var}' before using it, e.g. `int {var};`",
    "REDECLARATION":     "Remove the duplicate declaration or rename '{var}'.",
    "UNUSED_VAR":        "Either use '{var}' somewhere or remove its declaration.",
    "UNINITIALIZED_USE": "Assign a value to '{var}' before using it, e.g. `{var} = 0;`",
    "UNREACHABLE_CODE":  "Move or remove statements that appear after a return.",
}


@dataclass
class SemanticIssue:
    kind: str            # "ERROR" or "WARNING"
    code: str            # e.g. "UNDECLARED_VAR"
    message: str
    line: int
    variable: Optional[str] = None

    def hint(self) -> str:
        return _HINTS.get(self.code, "").replace("{var}", self.variable or "x")

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "code": self.code,
            "message": self.message,
            "line": self.line,
            "variable": self.variable,
            "hint": self.hint(),
        }


@dataclass
class SemanticResult:
    issues: List[SemanticIssue] = field(default_factory=list)
    symbol_table: Optional[SymbolTable] = None

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


# ── Semantic Analyzer ────────────────────────────────────────────────────────

class SemanticAnalyzer:
    """
    Recursive AST visitor that performs semantic checks and maintains
    a symbol table across all scopes.
    """

    def __init__(self) -> None:
        self.symbol_table = SymbolTable()
        self.issues: List[SemanticIssue] = []

    # ── Public entry point ──────────────────────────────────

    def analyze(self, ast_root) -> SemanticResult:
        self._visit(ast_root)
        # Check global scope for unused variables
        self._check_unused(self.symbol_table.scopes[0])
        return SemanticResult(issues=self.issues, symbol_table=self.symbol_table)

    # ── Visitor dispatch ────────────────────────────────────

    def _visit(self, node) -> None:
        if node is None:
            return
        handler = getattr(self, f"_v_{node.type.lower()}", self._v_children)
        handler(node)

    def _v_children(self, node) -> None:
        for child in node.children:
            self._visit(child)

    # ── Node visitors ───────────────────────────────────────

    def _v_program(self, node) -> None:
        for child in node.children:
            self._visit(child)

    def _v_functiondef(self, node) -> None:
        fn = node.value or ""
        line = node.line
        # Declare function name in global/current scope
        res = self.symbol_table.declare(fn, "function", line)
        if res == "REDECLARATION":
            self._err("REDECLARATION",
                      f"Function '{fn}' is already declared.", line, fn)
        else:
            self.symbol_table.mark_assigned(fn, line)

        # Function body is a Block child — enter its scope via _v_block
        self.symbol_table.enter_scope()
        for child in node.children:        # should be exactly one Block
            self._visit_block_stmts(child)
        scope = self.symbol_table.exit_scope()
        self._check_unused(scope)

    def _v_block(self, node) -> None:
        self.symbol_table.enter_scope()
        self._visit_block_stmts(node)
        scope = self.symbol_table.exit_scope()
        self._check_unused(scope)

    def _visit_block_stmts(self, node) -> None:
        """Visit statements inside a block, detecting unreachable code."""
        return_seen = False
        for stmt in node.children:
            if return_seen:
                self._warn("UNREACHABLE_CODE",
                           "Statement is unreachable (follows a return).",
                           stmt.line)
                break        # Only report once per block
            self._visit(stmt)
            if stmt.type == "Return":
                return_seen = True

    def _v_declaration(self, node) -> None:
        name = node.value
        line = node.line
        res = self.symbol_table.declare(name, "int", line)
        if res == "REDECLARATION":
            self._err("REDECLARATION",
                      f"Variable '{name}' is already declared in this scope.",
                      line, name)
        # If there's an initializer, visit it (RHS expressions) and mark assigned
        if node.children:
            self._visit(node.children[0])
            self.symbol_table.mark_assigned(name, line)

    def _v_assignment(self, node) -> None:
        # children[0] = Identifier (LHS), children[1] = Expression (RHS)
        if len(node.children) < 1:
            return
        lhs = node.children[0]
        var = lhs.value
        line = lhs.line or node.line

        sym = self.symbol_table.lookup(var)
        if sym is None:
            self._err("UNDECLARED_VAR",
                      f"Variable '{var}' is assigned but was never declared.",
                      line, var)
        else:
            self.symbol_table.mark_assigned(var, line)

        # Visit RHS (identifiers there will be checked via _v_identifier)
        if len(node.children) >= 2:
            self._visit(node.children[1])

    def _v_return(self, node) -> None:
        for child in node.children:
            self._visit(child)

    def _v_identifier(self, node) -> None:
        name = node.value
        line = node.line
        sym = self.symbol_table.lookup(name)
        if sym is None:
            self._err("UNDECLARED_VAR",
                      f"Variable '{name}' is used but was never declared.",
                      line, name)
        else:
            # Warn if used before any assignment (and it's a regular variable)
            if not sym.assigned and sym.type_ not in ("function", "builtin"):
                self._warn("UNINITIALIZED_USE",
                           f"Variable '{name}' may be used before being assigned a value.",
                           line, name)
            self.symbol_table.mark_used(name, line)

    def _v_expressionstatement(self, node) -> None:
        self._v_children(node)

    def _v_callexpression(self, node) -> None:
        callee = node.value or ""
        line = node.line
        sym = self.symbol_table.lookup(callee)
        if sym is None:
            self._warn("UNDECLARED_VAR",
                       f"Function '{callee}' is called but not declared.",
                       line, callee)
        else:
            self.symbol_table.mark_used(callee, line)
        # Visit arguments
        for arg in node.children:
            self._visit(arg)

    def _v_binaryop(self, node) -> None:
        self._v_children(node)

    def _v_number(self, node) -> None:
        pass

    def _v_string(self, node) -> None:
        pass

    # ── Helpers ─────────────────────────────────────────────

    def _err(self, code: str, msg: str, line: int, var: str = None) -> None:
        self.issues.append(SemanticIssue("ERROR", code, msg, line, var))

    def _warn(self, code: str, msg: str, line: int, var: str = None) -> None:
        # Deduplicate: don't add same warning code+var+line twice
        for existing in self.issues:
            if existing.code == code and existing.variable == var and existing.line == line:
                return
        self.issues.append(SemanticIssue("WARNING", code, msg, line, var))

    def _check_unused(self, scope: dict) -> None:
        for sym in scope.values():
            if sym.type_ in ("builtin", "function"):
                continue
            if not sym.used:
                self._warn("UNUSED_VAR",
                           f"Variable '{sym.name}' is declared but never used.",
                           sym.declared_line, sym.name)
