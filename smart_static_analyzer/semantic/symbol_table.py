"""
Symbol Table — scope-based variable tracker using dictionary stacks.
"""

BUILTINS = {
    "printf", "scanf", "sprintf", "sscanf", "fprintf", "malloc", "calloc", "realloc", 
    "free", "strlen", "strcpy", "strncpy", "strcat", "strcmp", "strncmp", "memcpy", 
    "memset", "memcmp", "puts", "gets", "fgets", "fputs", "getchar", "putchar", 
    "fopen", "fclose", "fread", "fwrite", "feof", "ferror", "fflush", "exit", 
    "abort", "atoi", "atof", "atol", "abs", "sqrt", "pow", "rand", "srand", 
    "time", "assert",
}


class Symbol:
    def __init__(self, name: str, type_: str, scope_level: int, declared_line: int, used: bool = False, assigned: bool = False, used_line: int | None = None, assigned_line: int | None = None):
        self.name = name
        self.type_ = type_
        self.scope_level = scope_level
        self.declared_line = declared_line
        self.used = used
        self.assigned = assigned
        self.used_line = used_line
        self.assigned_line = assigned_line

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
    def __init__(self):
        self.scopes = [{}]
        self.level = 0
        self._init_builtins()

    def _init_builtins(self):
        for name in BUILTINS:
            self.scopes[0][name] = Symbol(
                name=name, type_="builtin", scope_level=0, declared_line=0, used=True, assigned=True
            )

    def enter_scope(self):
        self.scopes.append({})
        self.level += 1

    def exit_scope(self) -> dict[str, Symbol]:
        if len(self.scopes) <= 1:
            return {}
        scope = self.scopes.pop()
        self.level -= 1
        return scope

    def declare(self, name: str, type_: str, line: int) -> str:
        if name in self.scopes[-1]:
            return "REDECLARATION"
        self.scopes[-1][name] = Symbol(name=name, type_=type_, scope_level=self.level, declared_line=line)
        return "OK"

    def lookup(self, name: str) -> Symbol | None:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def mark_used(self, name: str, line: int = 0) -> bool:
        for scope in reversed(self.scopes):
            if name in scope:
                sym = scope[name]
                sym.used = True
                if line and sym.used_line is None:
                    sym.used_line = line
                return True
        return False

    def mark_assigned(self, name: str, line: int = 0) -> bool:
        for scope in reversed(self.scopes):
            if name in scope:
                sym = scope[name]
                sym.assigned = True
                if line and sym.assigned_line is None:
                    sym.assigned_line = line
                return True
        return False

    def to_list(self) -> list[dict]:
        res = []
        for scope in self.scopes:
            for sym in scope.values():
                if sym.type_ != "builtin":
                    res.append(sym.to_dict())
        return res
