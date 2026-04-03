"""
Lexer for a C-like language — enhanced to handle real C code patterns.

Supported token types:
    PREPROCESSOR : #include, #define, #pragma, etc. (full line)
    KEYWORD      : int, return, void, if, else, while, for, ...
    IDENTIFIER   : variable/function names
    NUMBER       : integer and float literals
    STRING       : double-quoted string literals
    CHAR         : single-quoted character literals
    OPERATOR     : =, +, -, *, /, <, >, ==, !=, <=, >=, &&, ||, ++, --, etc.
    SYMBOL       : ; { } ( ) , [ ] . :

Line comments (//) and block comments (/* */) are silently skipped.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


# ---------- Token sets ----------

KEYWORDS = {
    "int", "return", "if", "else", "while", "for", "do",
    "void", "char", "float", "double", "long", "short",
    "unsigned", "signed", "struct", "union", "enum",
    "typedef", "const", "static", "extern", "auto", "register",
    "break", "continue", "switch", "case", "default",
    "sizeof", "NULL", "true", "false",
}

# Two-character operators — must be checked BEFORE single-char operators
OPERATORS_2 = {
    "==", "!=", "<=", ">=", "&&", "||",
    "++", "--", "+=", "-=", "*=", "/=", "%=",
    "->", "<<", ">>", "&=", "|=", "^=",
}

# Single-character operators
OPERATORS_1 = {
    "=", "+", "-", "*", "/", "<", ">",
    "!", "%", "&", "|", "^", "~", "?",
}

SYMBOLS = {";", "{", "}", "(", ")", ",", "[", "]", ".", ":"}


# ---------- Token & Error ----------

@dataclass
class Token:
    type: str
    value: str
    line: int

    def to_dict(self) -> dict:
        return {"type": self.type, "value": self.value, "line": self.line}


class LexicalError(Exception):
    def __init__(self, message: str, line: int):
        super().__init__(f"Lexical error on line {line}: {message}")
        self.line = line


# ---------- Lexer ----------

class Lexer:
    """Converts source code string into a list of Token objects."""

    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1

    # ── Primitives ───────────────────────────────────────────

    def _cur(self) -> str | None:
        return self.source[self.pos] if self.pos < len(self.source) else None

    def _peek(self, offset: int = 1) -> str | None:
        p = self.pos + offset
        return self.source[p] if p < len(self.source) else None

    def _advance(self) -> None:
        if self._cur() == "\n":
            self.line += 1
        self.pos += 1

    def _skip_whitespace(self) -> None:
        while (c := self._cur()) is not None and c in " \t\r\n":
            self._advance()

    # ── Comment skippers ─────────────────────────────────────

    def _skip_line_comment(self) -> None:
        """Skip from current position to end of line (after //)."""
        while (c := self._cur()) is not None and c != "\n":
            self._advance()

    def _skip_block_comment(self) -> None:
        """Skip /* ... */ block comment. Called after '/' consumed."""
        start_line = self.line
        self._advance()  # consume '*'
        while True:
            c = self._cur()
            if c is None:
                raise LexicalError("Unterminated block comment", start_line)
            if c == "*" and self._peek() == "/":
                self._advance()  # consume '*'
                self._advance()  # consume '/'
                return
            self._advance()

    # ── Preprocessor directive ───────────────────────────────

    def _read_preprocessor(self) -> Token:
        """Read entire # line as a PREPROCESSOR token."""
        start_line = self.line
        chars: list[str] = []
        while (c := self._cur()) is not None and c != "\n":
            chars.append(c)
            self._advance()
        return Token(type="PREPROCESSOR", value="".join(chars), line=start_line)

    # ── Literals ─────────────────────────────────────────────

    def _read_identifier(self) -> Token:
        start_line = self.line
        chars: list[str] = []
        while (c := self._cur()) is not None and (c.isalnum() or c == "_"):
            chars.append(c)
            self._advance()
        value = "".join(chars)
        return Token(type="KEYWORD" if value in KEYWORDS else "IDENTIFIER",
                     value=value, line=start_line)

    def _read_number(self) -> Token:
        """Read integer or floating-point literal."""
        start_line = self.line
        chars: list[str] = []
        # Hex literal
        if self._cur() == "0" and self._peek() in ("x", "X"):
            chars += ["0", self._peek()]
            self._advance(); self._advance()
            while (c := self._cur()) is not None and (c in "0123456789abcdefABCDEF"):
                chars.append(c); self._advance()
        else:
            while (c := self._cur()) is not None and c.isdigit():
                chars.append(c); self._advance()
            # Optional fractional part
            if self._cur() == "." and self._peek() is not None and self._peek().isdigit():
                chars.append("."); self._advance()
                while (c := self._cur()) is not None and c.isdigit():
                    chars.append(c); self._advance()
        # Suffix: u, l, f, ul, ll, etc.
        while (c := self._cur()) is not None and c in "uUlLfF":
            chars.append(c); self._advance()
        return Token(type="NUMBER", value="".join(chars), line=start_line)

    def _read_string(self) -> Token:
        start_line = self.line
        self._advance()  # opening "
        chars: list[str] = []
        escapes = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "0": "\0"}
        while True:
            c = self._cur()
            if c is None:
                raise LexicalError("Unterminated string literal", start_line)
            if c == "\n":
                raise LexicalError("Unterminated string literal (newline)", start_line)
            if c == '"':
                self._advance(); break
            if c == "\\":
                self._advance()
                esc = self._cur()
                if esc is None:
                    raise LexicalError("Unterminated escape sequence", start_line)
                chars.append(escapes.get(esc, esc))
                self._advance()
            else:
                chars.append(c); self._advance()
        return Token(type="STRING", value="".join(chars), line=start_line)

    def _read_char_literal(self) -> Token:
        start_line = self.line
        self._advance()  # opening '
        c = self._cur()
        if c == "\\":
            self._advance()
            c = self._cur()
            self._advance()
            value = "\\" + (c or "")
        else:
            value = c or ""
            self._advance()
        if self._cur() == "'":
            self._advance()
        return Token(type="CHAR", value=value, line=start_line)

    # ── Main tokenise loop ────────────────────────────────────

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []
        while (c := self._cur()) is not None:

            # Whitespace
            if c in " \t\r\n":
                self._skip_whitespace()
                continue

            # Preprocessor directive
            if c == "#":
                tokens.append(self._read_preprocessor())
                continue

            # Identifiers / keywords
            if c.isalpha() or c == "_":
                tokens.append(self._read_identifier())
                continue

            # Numbers
            if c.isdigit():
                tokens.append(self._read_number())
                continue

            # String literal
            if c == '"':
                tokens.append(self._read_string())
                continue

            # Char literal
            if c == "'":
                tokens.append(self._read_char_literal())
                continue

            # / — could be divide, // comment, or /* comment
            if c == "/":
                nxt = self._peek()
                if nxt == "/":
                    self._advance(); self._advance()
                    self._skip_line_comment()
                    continue
                if nxt == "*":
                    self._advance()
                    self._skip_block_comment()
                    continue
                # plain division operator — fall through to operator check

            # Two-character operators
            two = self.source[self.pos: self.pos + 2]
            if two in OPERATORS_2:
                tokens.append(Token(type="OPERATOR", value=two, line=self.line))
                self._advance(); self._advance()
                continue

            # Single-character operators
            if c in OPERATORS_1:
                tokens.append(Token(type="OPERATOR", value=c, line=self.line))
                self._advance()
                continue

            # Symbols
            if c in SYMBOLS:
                tokens.append(Token(type="SYMBOL", value=c, line=self.line))
                self._advance()
                continue

            raise LexicalError(f"Unexpected character '{c}'", self.line)

        return tokens


def lex(source: str) -> List[Token]:
    """Convenience function."""
    return Lexer(source).tokenize()
