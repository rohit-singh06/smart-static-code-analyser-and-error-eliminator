"""
Symbol Table — scope-based variable tracker.

Uses a stack of dictionaries to support nested scopes.
Entering a block pushes a new scope; exiting pops it.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# Common C library functions pre-declared so they don't trigger UNDECLARED errors
_BUILTINS = {
    "printf", "scanf", "sprintf", "sscanf", "fprintf",
    "malloc", "calloc", "realloc", "free",
    "strlen", "strcpy", "strncpy", "strcat", "strcmp", "strncmp",
    "memcpy", "memset", "memcmp",
    "puts", "gets", "fgets", "fputs", "getchar", "putchar",
    "fopen", "fclose", "fread", "fwrite", "feof", "ferror", "fflush",
    "exit", "abort", "atoi", "atof", "atol",
    "abs", "sqrt", "pow", "rand", "srand", "time",
    "assert",
}


@dataclass
class Symbol:
    name: str
    type_: str          # 'int', 'void', 'char', 'float', 'function', 'builtin', ...
    scope_level: int
    declared_line: int
    used: bool = False
    assigned: bool = False
    used_line: Optional[int] = None
    assigned_line: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type_,
            "scope_level": self.scope_level,
            "declared_line": self.declared_line,
            "used": self.used,
            "assigned": self.assigned,
            "used_line": self.used_line,
            "assigned_line": self.assigned_line,
        }


class SymbolTable:
    """Stack-based symbol table for nested scope management."""

    def __init__(self) -> None:
        self.scopes: list[dict[str, Symbol]] = [{}]
        self.level: int = 0
        self._init_builtins()

    def _init_builtins(self) -> None:
        for name in _BUILTINS:
            self.scopes[0][name] = Symbol(
                name=name, type_="builtin", scope_level=0,
                declared_line=0, used=True, assigned=True,
            )

    # ── Scope management ───────────────────────────────────

    def enter_scope(self) -> None:
        """Push a new scope onto the stack."""
        self.scopes.append({})
        self.level += 1

    def exit_scope(self) -> dict[str, Symbol]:
        """Pop the current scope and return its symbols (for unused-var check)."""
        if len(self.scopes) <= 1:
            return {}
        scope = self.scopes.pop()
        self.level -= 1
        return scope

    # ── Symbol operations ───────────────────────────────────

    def declare(self, name: str, type_: str, line: int) -> str:
        """
        Declare a variable in the current scope.
        Returns 'REDECLARATION' if already declared here, else 'OK'.
        """
        if name in self.scopes[-1]:
            return "REDECLARATION"
        self.scopes[-1][name] = Symbol(
            name=name, type_=type_,
            scope_level=self.level,
            declared_line=line,
        )
        return "OK"

    def lookup(self, name: str) -> Optional[Symbol]:
        """Search all scopes from innermost to outermost."""
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def mark_used(self, name: str, line: int = 0) -> bool:
        for scope in reversed(self.scopes):
            if name in scope:
                scope[name].used = True
                if line and scope[name].used_line is None:
                    scope[name].used_line = line
                return True
        return False

    def mark_assigned(self, name: str, line: int = 0) -> bool:
        for scope in reversed(self.scopes):
            if name in scope:
                scope[name].assigned = True
                if line and scope[name].assigned_line is None:
                    scope[name].assigned_line = line
                return True
        return False

    # ── Serialisation ───────────────────────────────────────

    def to_list(self) -> list[dict]:
        """Return all non-builtin symbols across all current scopes."""
        result = []
        for scope in self.scopes:
            for sym in scope.values():
                if sym.type_ != "builtin":
                    result.append(sym.to_dict())
        return result
