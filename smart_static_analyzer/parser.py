"""
Recursive descent parser for the small C-like language.

Grammar (extended):
    Program           → FunctionDefList | StatementList

    FunctionDefList   → FunctionDef FunctionDefList | ε
    FunctionDef       → 'int' IDENTIFIER '(' ')' Block       // simple function, e.g. int main() { ... }

    StatementList     → Statement StatementList | ε

    Statement         → Declaration
                      | Assignment
                      | ReturnStatement
                      | Block
                      | ExpressionStatement

    Declaration       → 'int' IDENTIFIER ('=' Expression)? ';'
    Assignment        → IDENTIFIER '=' Expression ';'
    ReturnStatement   → 'return' ';'
    Block             → '{' StatementList '}'
    ExpressionStatement → Expression ';'

    Expression        → Term ((+ | -) Term)*
    Term              → IDENTIFIER [ '(' ArgList? ')' ]
                      | NUMBER

    ArgList           → Expression (',' Expression)*
"""

from __future__ import annotations

from typing import List

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
    function_def_node,
    expression_stmt_node,
    call_expression_node,
)


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
    def parse(self) -> ASTNode:
        """Parse tokens into a Program AST node."""
        # Heuristic: if input starts with 'int' IDENT '(' it's a function definition list.
        if (
            len(self.tokens) >= 3
            and self.tokens[0].type == "KEYWORD"
            and self.tokens[0].value == "int"
            and self.tokens[1].type == "IDENTIFIER"
            and self.tokens[2].type == "SYMBOL"
            and self.tokens[2].value == "("
        ):
            functions: List[ASTNode] = []
            while self._current() is not None:
                tok = self._current()
                if not (tok.type == "KEYWORD" and tok.value == "int"):
                    break
                functions.append(self._parse_function_def())
            return program_node(functions)

        # Default: just a list of statements (previous behavior).
        statements: List[ASTNode] = self._parse_statement_list()
        return program_node(statements)

    def _parse_function_def(self) -> ASTNode:
        """
        FunctionDef → 'int' IDENTIFIER '(' ')' Block
        Currently supports only simple no-parameter functions like: int main() { ... }
        """
        self._match(expected_type="KEYWORD", expected_value="int")
        ident = self._match(expected_type="IDENTIFIER")
        self._match(expected_type="SYMBOL", expected_value="(")
        self._match(expected_type="SYMBOL", expected_value=")")
        body = self._parse_block()

        func = function_def_node(ident.value)
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
            stmts.append(self._parse_statement())
        return stmts

    def _parse_statement(self) -> ASTNode:
        token = self._current()
        if token is None:
            raise ParseError("Unexpected end of input in statement", 1)

        # Declaration: 'int' IDENTIFIER ('=' Expression)? ';'
        if token.type == "KEYWORD" and token.value == "int":
            return self._parse_declaration()

        # Return: 'return' ';'
        if token.type == "KEYWORD" and token.value == "return":
            return self._parse_return()

        # Block: '{' StatementList '}'
        if token.type == "SYMBOL" and token.value == "{":
            return self._parse_block()

        # Assignment or expression statement starting with IDENTIFIER
        if token.type == "IDENTIFIER":
            # Look ahead to decide between assignment and expression-statement/function call.
            next_tok = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
            if next_tok is not None and next_tok.type == "OPERATOR" and next_tok.value == "=":
                return self._parse_assignment()
            # Otherwise treat as a general expression statement (e.g., function call).
            expr = self._parse_expression()
            self._match(expected_type="SYMBOL", expected_value=";")
            return expression_stmt_node(expr)

        raise ParseError(f"Unexpected token '{token.value}'", token.line)

    def _parse_declaration(self) -> ASTNode:
        # 'int' IDENTIFIER ('=' Expression)? ';'
        self._match(expected_type="KEYWORD", expected_value="int")
        ident = self._match(expected_type="IDENTIFIER")
        node = declaration_node(ident.value)

        # Optional initializer
        token = self._current()
        if token is not None and token.type == "OPERATOR" and token.value == "=":
            self._match(expected_type="OPERATOR", expected_value="=")
            init_expr = self._parse_expression()
            node.add_child(init_expr)

        self._match(expected_type="SYMBOL", expected_value=";")
        return node

    def _parse_assignment(self) -> ASTNode:
        # IDENTIFIER '=' Expression ';'
        ident = self._match(expected_type="IDENTIFIER")
        eq = self._match(expected_type="OPERATOR", expected_value="=")

        assign = assignment_node()
        assign.add_child(identifier_node(ident.value))

        expr = self._parse_expression()
        assign.add_child(expr)

        self._match(expected_type="SYMBOL", expected_value=";")
        return assign

    def _parse_return(self) -> ASTNode:
        # 'return' ';'
        ret = self._match(expected_type="KEYWORD", expected_value="return")
        self._match(expected_type="SYMBOL", expected_value=";")
        return return_node()

    def _parse_block(self) -> ASTNode:
        # '{' StatementList '}'
        lbrace = self._match(expected_type="SYMBOL", expected_value="{")
        stmts = self._parse_statement_list()
        self._match(expected_type="SYMBOL", expected_value="}")
        return block_node(stmts)

    # Expressions ---------------------------------------------------------
    def _parse_expression(self) -> ASTNode:
        """
        Expression → Term ((+ | -) Term)*
        """
        left = self._parse_term()
        while True:
            token = self._current()
            if token is None or token.type != "OPERATOR" or token.value not in {"+", "-"}:
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
        Term → IDENTIFIER [ '(' ArgList? ')' ] | NUMBER
        """
        token = self._current()
        if token is None:
            raise ParseError("Unexpected end of input in expression", 1)

        if token.type == "IDENTIFIER":
            ident = self._match(expected_type="IDENTIFIER")
            # Possible function call: IDENTIFIER '(' ... ')'
            next_tok = self._current()
            if next_tok is not None and next_tok.type == "SYMBOL" and next_tok.value == "(":
                self._match(expected_type="SYMBOL", expected_value="(")
                args: List[ASTNode] = []
                # ArgList?  → Expression (',' Expression)*
                if not (self._current() and self._current().type == "SYMBOL" and self._current().value == ")"):
                    args.append(self._parse_expression())
                    while True:
                        tok = self._current()
                        if tok is None or not (tok.type == "SYMBOL" and tok.value == ","):
                            break
                        self._match(expected_type="SYMBOL", expected_value=",")
                        args.append(self._parse_expression())
                self._match(expected_type="SYMBOL", expected_value=")")

                call = call_expression_node(ident.value)
                for a in args:
                    call.add_child(a)
                return call

            # Plain identifier
            return identifier_node(ident.value)

        if token.type == "NUMBER":
            num = self._match(expected_type="NUMBER")
            return number_node(int(num.value))

        raise ParseError(f"Expected IDENTIFIER or NUMBER, got '{token.value}'", token.line)


def parse(tokens: List[Token]) -> ASTNode:
    """Convenience function."""
    return Parser(tokens).parse()

