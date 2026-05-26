"""
Lexer for a C-like language.
Supported tokens: PREPROCESSOR, KEYWORD, IDENTIFIER, NUMBER, STRING, CHAR, OPERATOR, SYMBOL.
Comments are skipped.
"""

KEYWORDS = {
    "int", "return", "if", "else", "while", "for", "do", "void", "char", "float", 
    "double", "long", "short", "unsigned", "signed", "struct", "union", "enum",
    "typedef", "const", "static", "extern", "auto", "register", "break", 
    "continue", "switch", "case", "default", "sizeof", "NULL", "true", "false",
}

OPERATORS_2 = {
    "==", "!=", "<=", ">=", "&&", "||", "++", "--", "+=", "-=", "*=", "/=", "%=",
    "->", "<<", ">>", "&=", "|=", "^=",
}

OPERATORS_1 = {"=", "+", "-", "*", "/", "<", ">", "!", "%", "&", "|", "^", "~", "?",}

SYMBOLS = {";", "{", "}", "(", ")", ",", "[", "]", ".", ":"}


class Token:
    def __init__(self, type: str, value: str, line: int):
        self.type = type
        self.value = value
        self.line = line

    def to_dict(self) -> dict:
        return {"type": self.type, "value": self.value, "line": self.line}


class LexicalError(Exception):
    def __init__(self, message: str, line: int):
        super().__init__(f"Lexical error on line {line}: {message}")
        self.line = line


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1

    def _cur(self) -> str | None:
        return self.source[self.pos] if self.pos < len(self.source) else None

    def _peek(self, offset: int = 1) -> str | None:
        p = self.pos + offset
        return self.source[p] if p < len(self.source) else None

    def _advance(self) -> None:
        if self._cur() == "\n":
            self.line += 1
        self.pos += 1

    def tokenize(self) -> list[Token]:
        tokens = []
        while (c := self._cur()) is not None:
            # Whitespace
            if c in " \t\r\n":
                self._advance()
                continue

            # Preprocessor directives (lines starting with #)
            if c == "#":
                start_line = self.line
                chars = []
                while (c := self._cur()) is not None and c != "\n":
                    chars.append(c)
                    self._advance()
                tokens.append(Token("PREPROCESSOR", "".join(chars), start_line))
                continue

            # Identifiers and Keywords
            if c.isalpha() or c == "_":
                start_line = self.line
                chars = []
                while (c := self._cur()) is not None and (c.isalnum() or c == "_"):
                    chars.append(c)
                    self._advance()
                val = "".join(chars)
                tokens.append(Token("KEYWORD" if val in KEYWORDS else "IDENTIFIER", val, start_line))
                continue

            # Numbers (Hexadecimal, Decimals, Floats)
            if c.isdigit():
                start_line = self.line
                chars = []
                if c == "0" and self._peek() in ("x", "X"):
                    chars += ["0", self._peek()]
                    self._advance()
                    self._advance()
                    while (c := self._cur()) is not None and c in "0123456789abcdefABCDEF":
                        chars.append(c)
                        self._advance()
                else:
                    while (c := self._cur()) is not None and c.isdigit():
                        chars.append(c)
                        self._advance()
                    if self._cur() == "." and self._peek() is not None and self._peek().isdigit():
                        chars.append(".")
                        self._advance()
                        while (c := self._cur()) is not None and c.isdigit():
                            chars.append(c)
                            self._advance()
                # Suffixes: u, l, f, etc.
                while (c := self._cur()) is not None and c in "uUlLfF":
                    chars.append(c)
                    self._advance()
                tokens.append(Token("NUMBER", "".join(chars), start_line))
                continue

            # Double-quoted String Literals
            if c == '"':
                start_line = self.line
                self._advance()  # consume '"'
                chars = []
                escapes = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "0": "\0"}
                while True:
                    c = self._cur()
                    if c is None or c == "\n":
                        raise LexicalError("Unterminated string literal", start_line)
                    if c == '"':
                        self._advance()
                        break
                    if c == "\\":
                        self._advance()
                        esc = self._cur()
                        if esc is None:
                            raise LexicalError("Unterminated escape sequence", start_line)
                        chars.append(escapes.get(esc, esc))
                        self._advance()
                    else:
                        chars.append(c)
                        self._advance()
                tokens.append(Token("STRING", "".join(chars), start_line))
                continue

            # Single-quoted Char Literals
            if c == "'":
                start_line = self.line
                self._advance()
                char_val = self._cur() or ""
                if char_val == "\\":
                    self._advance()
                    char_val = "\\" + (self._cur() or "")
                self._advance()
                if self._cur() == "'":
                    self._advance()
                tokens.append(Token("CHAR", char_val, start_line))
                continue

            # Comments (// or /*) and Division Operator
            if c == "/":
                nxt = self._peek()
                if nxt == "/":
                    self._advance()
                    self._advance()
                    while (c := self._cur()) is not None and c != "\n":
                        self._advance()
                    continue
                if nxt == "*":
                    start_line = self.line
                    self._advance()
                    self._advance()
                    while True:
                        c = self._cur()
                        if c is None:
                            raise LexicalError("Unterminated block comment", start_line)
                        if c == "*" and self._peek() == "/":
                            self._advance()
                            self._advance()
                            break
                        self._advance()
                    continue

            # Two-character Operators
            two = self.source[self.pos : self.pos + 2]
            if two in OPERATORS_2:
                tokens.append(Token("OPERATOR", two, self.line))
                self._advance()
                self._advance()
                continue

            # Single-character Operators
            if c in OPERATORS_1:
                tokens.append(Token("OPERATOR", c, self.line))
                self._advance()
                continue

            # Symbols
            if c in SYMBOLS:
                tokens.append(Token("SYMBOL", c, self.line))
                self._advance()
                continue

            raise LexicalError(f"Unexpected character '{c}'", self.line)

        return tokens


def lex(source: str) -> list[Token]:
    return Lexer(source).tokenize()
