"""
Lexer for a small C-like language.

Supported token types:
    - KEYWORD   : 'int', 'return'
    - IDENTIFIER: variable names (letters, digits, underscore, starting with letter/_)
    - NUMBER    : integer literals
    - OPERATOR  : = + - * /
    - SYMBOL    : ; { } ( )

Each token has (type, value, line).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


KEYWORDS = {"int", "return"}
OPERATORS = {"=", "+", "-", "*", "/"}
SYMBOLS = {";", "{", "}", "(", ")"}


@dataclass
class Token:
    type: str
    value: str
    line: int

    def to_dict(self) -> dict:
        return {"type": self.type, "value": self.value, "line": self.line}


class LexicalError(Exception):
    """Raised when an invalid character or token is encountered."""

    def __init__(self, message: str, line: int):
        super().__init__(f"Lexical error on line {line}: {message}")
        self.line = line


class Lexer:
    """Converts source code string into a list of Token objects."""

    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1

    def _current_char(self) -> str | None:
        if self.pos >= len(self.source):
            return None
        return self.source[self.pos]

    def _advance(self) -> None:
        c = self._current_char()
        if c == "\n":
            self.line += 1
        self.pos += 1

    def _skip_whitespace(self) -> None:
        while (c := self._current_char()) is not None and c in " \t\r\n":
            self._advance()

    def _identifier_or_keyword(self) -> Token:
        start_line = self.line
        value_chars: list[str] = []
        c = self._current_char()
        while c is not None and (c.isalnum() or c == "_"):
            value_chars.append(c)
            self._advance()
            c = self._current_char()
        value = "".join(value_chars)
        token_type = "KEYWORD" if value in KEYWORDS else "IDENTIFIER"
        return Token(type=token_type, value=value, line=start_line)

    def _number(self) -> Token:
        start_line = self.line
        digits: list[str] = []
        c = self._current_char()
        while c is not None and c.isdigit():
            digits.append(c)
            self._advance()
            c = self._current_char()
        return Token(type="NUMBER", value="".join(digits), line=start_line)

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []
        while (c := self._current_char()) is not None:
            if c in " \t\r\n":
                self._skip_whitespace()
                continue

            if c.isalpha() or c == "_":
                tokens.append(self._identifier_or_keyword())
                continue

            if c.isdigit():
                tokens.append(self._number())
                continue

            if c in OPERATORS:
                tokens.append(Token(type="OPERATOR", value=c, line=self.line))
                self._advance()
                continue

            if c in SYMBOLS:
                tokens.append(Token(type="SYMBOL", value=c, line=self.line))
                self._advance()
                continue

            # Anything else is considered invalid for now
            raise LexicalError(f"Invalid character '{c}'", self.line)

        return tokens


def lex(source: str) -> List[Token]:
    """Convenience function."""
    return Lexer(source).tokenize()

