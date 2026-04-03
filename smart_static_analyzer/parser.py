"""
Recursive descent parser for a C-like language.

Grammar (extended):
    Program           → FunctionDefList | StatementList

    FunctionDefList   → FunctionDef FunctionDefList | ε
    FunctionDef       → TypeKW IDENTIFIER '(' ')' Block

    StatementList     → (PREPROCESSOR | Statement) StatementList | ε

    Statement         → Declaration
                      | Assignment
                      | ReturnStatement
                      | Block
                      | ExpressionStatement

    Declaration       → TypeKW IDENTIFIER ('=' Expression)? ';'
    Assignment        → IDENTIFIER '=' Expression ';'
    ReturnStatement   → 'return' Expression? ';'
    Block             → '{' StatementList '}'
    ExpressionStatement → Expression ';'

    Expression        → Term ((+ | - | * | / | < | > | == | != | <= | >=) Term)*
    Term              → IDENTIFIER [ '(' ArgList? ')' ]
                      | NUMBER | CHAR | STRING | '(' Expression ')'

    ArgList           → Expression (',' Expression)*

    TypeKW            → 'int' | 'void' | 'char' | 'float' | 'double'
                       | 'long' | 'short' | 'unsigned' | 'signed'
"""

from __future__ import annotations

from typing import List

try:
    from .lexer import Token
    from .ast_nodes import (
        ASTNode,
        program_node,
        declaration_node,
        assignment_node,
        return_node,
        block_node,
        binary_op_node,
        identifier_node,
        number_node,
        string_node,
        function_def_node,
        expression_stmt_node,
        call_expression_node,
    )
except ImportError:
    from lexer import Token
    from ast_nodes import (
        ASTNode,
        program_node,
        declaration_node,
        assignment_node,
        return_node,
        block_node,
        binary_op_node,
        identifier_node,
        number_node,
        string_node,
        function_def_node,
        expression_stmt_node,
        call_expression_node,
    )

# All keywords that can start a type declaration or function return type
TYPE_KEYWORDS = {
    "int", "void", "char", "float", "double",
    "long", "short", "unsigned", "signed",
}

BINARY_OPERATORS = {"+", "-", "*", "/", "%", "<", ">", "==", "!=", "<=", ">=", "&&", "||"}


class ParseError(Exception):
    """Raised when a syntax error is encountered."""

    def __init__(self, message: str, line: int):
        super().__init__(f"Syntax error on line {line}: {message}")
        self.line = line


class Parser:
    """Recursive descent parser that builds an AST from tokens."""

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def _current(self) -> Token | None:
        if self.pos >= len(self.tokens):
            return None
        return self.tokens[self.pos]

    def _advance(self) -> None:
        if self.pos < len(self.tokens):
            self.pos += 1

    def _match(self, expected_type: str | None = None, expected_value: str | None = None) -> Token:
        token = self._current()
        if token is None:
            raise ParseError("Unexpected end of input", self.tokens[-1].line if self.tokens else 1)

        if expected_type is not None and token.type != expected_type:
            raise ParseError(f"Expected token type {expected_type}, got {token.type}", token.line)
        if expected_value is not None and token.value != expected_value:
            raise ParseError(f"Expected '{expected_value}', got '{token.value}'", token.line)

        self._advance()
        return token

    # Entry point ---------------------------------------------------------
    def _is_type_keyword(self, tok: Token | None) -> bool:
        return tok is not None and tok.type == "KEYWORD" and tok.value in TYPE_KEYWORDS

    def _skip_type_qualifiers(self) -> None:
        """Consume optional type qualifiers: const, static, extern, volatile."""
        qualifiers = {"const", "static", "extern", "volatile", "register", "auto"}
        while True:
            tok = self._current()
            if tok and tok.type == "KEYWORD" and tok.value in qualifiers:
                self._advance()
            else:
                break

    def parse(self) -> ASTNode:
        """Parse tokens into a Program AST node."""
        # Skip leading preprocessor tokens and qualifiers to find real start
        temp_pos = self.pos
        while temp_pos < len(self.tokens) and self.tokens[temp_pos].type == "PREPROCESSOR":
            temp_pos += 1

        # Heuristic: TypeKW IDENT '(' → function definition list
        if (
            temp_pos + 2 < len(self.tokens)
            and self._is_type_keyword(self.tokens[temp_pos])
            and self.tokens[temp_pos + 1].type == "IDENTIFIER"
            and self.tokens[temp_pos + 2].type == "SYMBOL"
            and self.tokens[temp_pos + 2].value == "("
        ):
            # Consume leading preprocessor tokens first
            while self._current() and self._current().type == "PREPROCESSOR":
                self._advance()
            functions: List[ASTNode] = []
            while self._current() is not None:
                tok = self._current()
                if tok.type == "PREPROCESSOR":
                    self._advance(); continue
                if not self._is_type_keyword(tok):
                    break
                functions.append(self._parse_function_def())
            return program_node(functions)

        statements: List[ASTNode] = self._parse_statement_list()
        return program_node(statements)

    def _parse_function_def(self) -> ASTNode:
        """
        FunctionDef → TypeKW IDENTIFIER '(' ParamList? ')' Block
        """
        self._skip_type_qualifiers()
        while self._is_type_keyword(self._current()):
            self._advance()
        ident = self._match(expected_type="IDENTIFIER")
        self._match(expected_type="SYMBOL", expected_value="(")
        depth = 1
        while self._current() is not None and depth > 0:
            v = self._current().value; t = self._current().type
            if t == "SYMBOL" and v == "(": depth += 1
            elif t == "SYMBOL" and v == ")": depth -= 1
            self._advance()
        body = self._parse_block()
        func = function_def_node(ident.value, line=ident.line)
        func.add_child(body)
        return func

    # Statement list and statements --------------------------------------
    def _parse_statement_list(self) -> List[ASTNode]:
        stmts: List[ASTNode] = []
        while True:
            token = self._current()
            if token is None:
                break
            if token.type == "SYMBOL" and token.value == "}":
                break
            # Silently skip preprocessor directives inside blocks
            if token.type == "PREPROCESSOR":
                self._advance()
                continue
            stmts.append(self._parse_statement())
        return stmts

    def _parse_statement(self) -> ASTNode:
        token = self._current()
        if token is None:
            raise ParseError("Unexpected end of input in statement", 1)

        # Skip type qualifiers (const, static, etc.) before type keywords
        self._skip_type_qualifiers()
        token = self._current()
        if token is None:
            raise ParseError("Unexpected end of input after qualifier", 1)

        # Declaration: TypeKW IDENTIFIER ...
        if self._is_type_keyword(token):
            return self._parse_declaration()

        # Return
        if token.type == "KEYWORD" and token.value == "return":
            return self._parse_return()

        # Block
        if token.type == "SYMBOL" and token.value == "{":
            return self._parse_block()

        # Assignment or expression statement starting with IDENTIFIER
        if token.type == "IDENTIFIER":
            next_tok = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
            if next_tok is not None and next_tok.type == "OPERATOR" and next_tok.value == "=":
                return self._parse_assignment()
            expr = self._parse_expression()
            self._match(expected_type="SYMBOL", expected_value=";")
            return expression_stmt_node(expr)

        # Unknown keyword or token — skip it gracefully to avoid hard crash
        if token.type == "KEYWORD":
            self._advance()
            # consume until ';' or '}'
            while self._current() and not (
                (self._current().type == "SYMBOL" and self._current().value in (";", "{", "}"))
            ):
                self._advance()
            if self._current() and self._current().value == ";":
                self._advance()
            return expression_stmt_node(identifier_node(f"[{token.value}…]"))

        raise ParseError(f"Unexpected token '{token.value}'", token.line)

    def _parse_declaration(self) -> ASTNode:
        while self._is_type_keyword(self._current()):
            self._advance()
        while self._current() and self._current().type == "OPERATOR" and self._current().value == "*":
            self._advance()
        ident = self._match(expected_type="IDENTIFIER")
        node = declaration_node(ident.value, line=ident.line)
        if self._current() and self._current().type == "SYMBOL" and self._current().value == "[":
            self._advance()
            while self._current() and self._current().value != "]":
                self._advance()
            if self._current(): self._advance()
        token = self._current()
        if token is not None and token.type == "OPERATOR" and token.value == "=":
            self._advance()
            node.add_child(self._parse_expression())
        self._match(expected_type="SYMBOL", expected_value=";")
        return node

    def _parse_assignment(self) -> ASTNode:
        ident = self._match(expected_type="IDENTIFIER")
        self._match(expected_type="OPERATOR", expected_value="=")
        assign = assignment_node(line=ident.line)
        assign.add_child(identifier_node(ident.value, line=ident.line))
        assign.add_child(self._parse_expression())
        self._match(expected_type="SYMBOL", expected_value=";")
        return assign

    def _parse_return(self) -> ASTNode:
        ret_tok = self._match(expected_type="KEYWORD", expected_value="return")
        node = return_node(line=ret_tok.line)
        tok = self._current()
        if tok is not None and not (tok.type == "SYMBOL" and tok.value == ";"):
            node.add_child(self._parse_expression())
        self._match(expected_type="SYMBOL", expected_value=";")
        return node

    def _parse_block(self) -> ASTNode:
        lbrace = self._match(expected_type="SYMBOL", expected_value="{")
        stmts = self._parse_statement_list()
        self._match(expected_type="SYMBOL", expected_value="}")
        return block_node(stmts, line=lbrace.line)

    # Expressions ---------------------------------------------------------
    def _parse_expression(self) -> ASTNode:
        """
        Expression → Term (BinaryOp Term)*
        Supports arithmetic, comparison, logical operators.
        """
        left = self._parse_term()
        while True:
            token = self._current()
            if token is None or token.type != "OPERATOR" or token.value not in BINARY_OPERATORS:
                break
            op_token = self._match(expected_type="OPERATOR")
            right = self._parse_term()
            op_node = binary_op_node(op_token.value)
            op_node.add_child(left)
            op_node.add_child(right)
            left = op_node
        return left

    def _parse_term(self) -> ASTNode:
        """
        Term → IDENTIFIER [ '(' ArgList? ')' ] | NUMBER | CHAR | STRING
             | '(' Expression ')'
             | UnaryOp Term
        """
        token = self._current()
        if token is None:
            raise ParseError("Unexpected end of input in expression", 1)

        # Parenthesised expression
        if token.type == "SYMBOL" and token.value == "(":
            self._match(expected_type="SYMBOL", expected_value="(")
            inner = self._parse_expression()
            self._match(expected_type="SYMBOL", expected_value=")")
            return inner

        # Unary operators: -, !, ~, &, *
        if token.type == "OPERATOR" and token.value in ("-", "!", "~", "&", "*", "++", "--"):
            op = self._match(expected_type="OPERATOR")
            operand = self._parse_term()
            node = binary_op_node(f"unary{op.value}")
            node.add_child(operand)
            return node

        if token.type == "IDENTIFIER":
            ident = self._match(expected_type="IDENTIFIER")
            if self._current() and self._current().type == "SYMBOL" and self._current().value == "(":
                self._match(expected_type="SYMBOL", expected_value="(")
                args: List[ASTNode] = []
                if not (self._current() and self._current().type == "SYMBOL" and self._current().value == ")"):
                    args.append(self._parse_expression())
                    while self._current() and self._current().type == "SYMBOL" and self._current().value == ",":
                        self._advance()
                        args.append(self._parse_expression())
                self._match(expected_type="SYMBOL", expected_value=")")
                call = call_expression_node(ident.value, line=ident.line)
                for a in args:
                    call.add_child(a)
                return call
            if self._current() and self._current().type == "SYMBOL" and self._current().value == "[":
                self._advance()
                self._parse_expression()
                if self._current() and self._current().value == "]":
                    self._advance()
            return identifier_node(ident.value, line=ident.line)

        if token.type == "NUMBER":
            num = self._match(expected_type="NUMBER")
            try: val = int(num.value, 0)
            except ValueError: val = float(num.value)
            return number_node(val, line=num.line)

        if token.type in ("STRING", "CHAR"):
            s = self._match()
            return string_node(s.value, line=s.line)

        raise ParseError(f"Expected expression, got '{token.value}'", token.line)


def parse(tokens: List[Token]) -> ASTNode:
    """Convenience function."""
    return Parser(tokens).parse()

