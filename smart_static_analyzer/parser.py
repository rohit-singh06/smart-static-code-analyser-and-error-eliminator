"""
Recursive descent parser for a C-like language.
Builds an AST node tree from a list of Tokens.
"""

from typing import List
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

TYPE_KEYWORDS = {"int", "void", "char", "float", "double", "long", "short", "unsigned", "signed"}
BINARY_OPERATORS = {"+", "-", "*", "/", "%", "<", ">", "==", "!=", "<=", ">=", "&&", "||"}
ASSIGNMENT_OPERATORS = {"=", "+=", "-=", "*=", "/=", "%="}

TYPE_CANONICAL = {
    "int": "int", "long": "long", "short": "short", "char": "char",
    "float": "float", "double": "double", "void": "void",
}
TYPE_MODIFIERS = {"unsigned", "signed"}


class ParseError(Exception):
    def __init__(self, message: str, line: int):
        super().__init__(f"Syntax error on line {line}: {message}")
        self.line = line


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def _cur(self) -> Token | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _advance(self) -> None:
        if self.pos < len(self.tokens):
            self.pos += 1

    def _match(self, type_expected: str = None, value_expected: str = None) -> Token:
        tok = self._cur()
        if tok is None:
            raise ParseError("Unexpected end of input", self.tokens[-1].line if self.tokens else 1)

        if type_expected is not None and tok.type != type_expected:
            raise ParseError(f"Expected token type {type_expected}, got {tok.type}", tok.line)
        if value_expected is not None and tok.value != value_expected:
            raise ParseError(f"Expected '{value_expected}', got '{tok.value}'", tok.line)

        self._advance()
        return tok

    def _is_type_kw(self, tok: Token | None) -> bool:
        return tok is not None and tok.type == "KEYWORD" and tok.value in TYPE_KEYWORDS

    def _skip_qualifiers(self) -> None:
        qualifiers = {"const", "static", "extern", "volatile", "register", "auto"}
        while (tok := self._cur()) and tok.type == "KEYWORD" and tok.value in qualifiers:
            self._advance()

    def _canonical_type(self, type_parts: List[str]) -> str:
        base = [t for t in type_parts if t not in TYPE_MODIFIERS]
        if not base:
            return "int"
        return TYPE_CANONICAL.get(base[0], base[0])

    def parse(self) -> ASTNode:
        # Check if the code starts with a function definition pattern: TypeKW Identifier '('
        temp = self.pos
        while temp < len(self.tokens) and self.tokens[temp].type == "PREPROCESSOR":
            temp += 1

        if (
            temp + 2 < len(self.tokens)
            and self._is_type_kw(self.tokens[temp])
            and self.tokens[temp + 1].type == "IDENTIFIER"
            and self.tokens[temp + 2].type == "SYMBOL"
            and self.tokens[temp + 2].value == "("
        ):
            # Parse list of function definitions
            while self._cur() and self._cur().type == "PREPROCESSOR":
                self._advance()
            funcs = []
            while self._cur() is not None:
                tok = self._cur()
                if tok.type == "PREPROCESSOR":
                    self._advance()
                    continue
                if not self._is_type_kw(tok):
                    break
                funcs.append(self._parse_function())
            return program_node(funcs)

        # Parse statement list otherwise
        return program_node(self._parse_statement_list())

    def _parse_function(self) -> ASTNode:
        self._skip_qualifiers()
        while self._is_type_kw(self._cur()):
            self._advance()
        ident = self._match("IDENTIFIER")
        self._match("SYMBOL", "(")
        # Skip function parameters safely
        depth = 1
        while self._cur() is not None and depth > 0:
            v, t = self._cur().value, self._cur().type
            if t == "SYMBOL" and v == "(":
                depth += 1
            elif t == "SYMBOL" and v == ")":
                depth -= 1
            self._advance()
        body = self._parse_block()
        func = function_def_node(ident.value, line=ident.line)
        func.add_child(body)
        return func

    def _parse_statement_list(self) -> List[ASTNode]:
        stmts = []
        while True:
            tok = self._cur()
            if tok is None or (tok.type == "SYMBOL" and tok.value == "}"):
                break
            if tok.type == "PREPROCESSOR":
                self._advance()
                continue
            stmts.append(self._parse_statement())
        return stmts

    def _parse_statement(self) -> ASTNode:
        self._skip_qualifiers()
        tok = self._cur()
        if tok is None:
            raise ParseError("Unexpected end of input in statement", 1)

        if self._is_type_kw(tok):
            return self._parse_declaration()

        if tok.type == "KEYWORD" and tok.value == "return":
            return self._parse_return()

        if tok.type == "SYMBOL" and tok.value == "{":
            return self._parse_block()

        if tok.type == "IDENTIFIER":
            is_assign = False
            temp = self.pos + 1
            if temp < len(self.tokens) and self.tokens[temp].type == "SYMBOL" and self.tokens[temp].value == "[":
                depth = 1
                while temp < len(self.tokens) and depth > 0:
                    temp += 1
                    if self.tokens[temp].type == "SYMBOL" and self.tokens[temp].value == "[":
                        depth += 1
                    elif self.tokens[temp].type == "SYMBOL" and self.tokens[temp].value == "]":
                        depth -= 1
                if temp + 1 < len(self.tokens) and self.tokens[temp + 1].type == "OPERATOR" and self.tokens[temp + 1].value in ASSIGNMENT_OPERATORS:
                    is_assign = True
            elif temp < len(self.tokens) and self.tokens[temp].type == "OPERATOR" and self.tokens[temp].value in ASSIGNMENT_OPERATORS:
                is_assign = True

            if is_assign:
                return self._parse_assignment()
            expr = self._parse_expression()
            self._match("SYMBOL", ";")
            return expression_stmt_node(expr)

        if tok.type == "KEYWORD" and tok.value == "if":
            return self._parse_if()

        if tok.type == "KEYWORD" and tok.value == "while":
            return self._parse_while()

        if tok.type == "KEYWORD" and tok.value == "for":
            return self._parse_for()

        if tok.type == "KEYWORD" and tok.value in ("break", "continue"):
            self._advance()
            self._match("SYMBOL", ";")
            return ASTNode(tok.value.capitalize(), line=tok.line)

        if tok.type == "KEYWORD":
            self._advance()
            while self._cur() and not (self._cur().type == "SYMBOL" and self._cur().value in (";", "{", "}")):
                self._advance()
            if self._cur() and self._cur().value == ";":
                self._advance()
            return expression_stmt_node(identifier_node(f"[{tok.value}…]"))

        raise ParseError(f"Unexpected token '{tok.value}'", tok.line)

    def _parse_if(self) -> ASTNode:
        if_tok = self._match("KEYWORD", "if")
        self._match("SYMBOL", "(")
        cond = self._parse_expression()
        self._match("SYMBOL", ")")
        then_branch = self._parse_statement()
        node = ASTNode("If", line=if_tok.line)
        node.add_child(cond)
        node.add_child(then_branch)

        # Check for optional else branch
        if (tok := self._cur()) and tok.type == "KEYWORD" and tok.value == "else":
            self._advance()
            else_branch = self._parse_statement()
            node.add_child(else_branch)

        return node

    def _parse_while(self) -> ASTNode:
        while_tok = self._match("KEYWORD", "while")
        self._match("SYMBOL", "(")
        cond = self._parse_expression()
        self._match("SYMBOL", ")")
        body = self._parse_statement()
        node = ASTNode("While", line=while_tok.line)
        node.add_child(cond)
        node.add_child(body)
        return node

    def _parse_declaration(self) -> ASTNode:
        type_parts = []
        while self._is_type_kw(self._cur()):
            type_parts.append(self._cur().value)
            self._advance()
        canonical = self._canonical_type(type_parts)

        # Detect pointers: e.g., int* p;
        is_ptr = False
        while self._cur() and self._cur().type == "OPERATOR" and self._cur().value == "*":
            self._advance()
            is_ptr = True
        if is_ptr:
            canonical += "*"

        ident = self._match("IDENTIFIER")
        node = declaration_node(ident.value, line=ident.line)
        node.meta["var_type"] = canonical

        # Detect arrays: e.g., int arr[10];
        if self._cur() and self._cur().type == "SYMBOL" and self._cur().value == "[":
            self._advance()
            while self._cur() and self._cur().value != "]":
                self._advance()
            if self._cur():
                self._advance()
            node.meta["var_type"] = canonical + "[]"

        if self._cur() and self._cur().type == "OPERATOR" and self._cur().value == "=":
            self._advance()
            node.add_child(self._parse_expression())

        self._match("SYMBOL", ";")
        return node

    def _parse_assignment(self) -> ASTNode:
        ident = self._match("IDENTIFIER")
        is_subscripted = False
        if self._cur() and self._cur().type == "SYMBOL" and self._cur().value == "[":
            self._match("SYMBOL", "[")
            self._parse_expression()
            self._match("SYMBOL", "]")
            is_subscripted = True
        op_tok = self._match("OPERATOR")
        assign = assignment_node(line=ident.line)
        assign.value = op_tok.value
        lhs = identifier_node(ident.value, line=ident.line)
        if is_subscripted:
            lhs.meta["is_subscripted"] = True
        assign.add_child(lhs)
        assign.add_child(self._parse_expression())
        self._match("SYMBOL", ";")
        return assign

    def _parse_for(self) -> ASTNode:
        for_tok = self._match("KEYWORD", "for")
        self._match("SYMBOL", "(")

        init_node = None
        if self._cur() and self._cur().type == "SYMBOL" and self._cur().value == ";":
            self._advance()
        elif self._is_type_kw(self._cur()):
            init_node = self._parse_declaration()
        else:
            init_node = self._parse_expression()
            self._match("SYMBOL", ";")

        cond_node = None
        if self._cur() and self._cur().type == "SYMBOL" and self._cur().value == ";":
            self._advance()
        else:
            cond_node = self._parse_expression()
            self._match("SYMBOL", ";")

        step_node = None
        if self._cur() and self._cur().type == "SYMBOL" and self._cur().value == ")":
            pass
        else:
            step_node = self._parse_expression()

        self._match("SYMBOL", ")")
        body_node = self._parse_statement()

        node = ASTNode("For", line=for_tok.line)
        if init_node:
            node.add_child(init_node)
        else:
            node.add_child(ASTNode("EmptyInit", line=for_tok.line))

        if cond_node:
            node.add_child(cond_node)
        else:
            node.add_child(ASTNode("EmptyCond", line=for_tok.line))

        if step_node:
            node.add_child(step_node)
        else:
            node.add_child(ASTNode("EmptyStep", line=for_tok.line))

        node.add_child(body_node)
        return node

    def _parse_return(self) -> ASTNode:
        ret_tok = self._match("KEYWORD", "return")
        node = return_node(line=ret_tok.line)
        if self._cur() and not (self._cur().type == "SYMBOL" and self._cur().value == ";"):
            node.add_child(self._parse_expression())
        self._match("SYMBOL", ";")
        return node

    def _parse_block(self) -> ASTNode:
        lbrace = self._match("SYMBOL", "{")
        stmts = self._parse_statement_list()
        self._match("SYMBOL", "}")
        return block_node(stmts, line=lbrace.line)

    def _parse_expression(self) -> ASTNode:
        left = self._parse_term()
        while True:
            tok = self._cur()
            if tok is None or tok.type != "OPERATOR" or tok.value not in BINARY_OPERATORS:
                break
            op_tok = self._match("OPERATOR")
            right = self._parse_term()
            op_node = binary_op_node(op_tok.value)
            op_node.add_child(left)
            op_node.add_child(right)
            left = op_node
        return left

    def _parse_term(self) -> ASTNode:
        tok = self._cur()
        if tok is None:
            raise ParseError("Unexpected end of input in expression", 1)

        # Parenthesized expression: ( expr )
        if tok.type == "SYMBOL" and tok.value == "(":
            self._match("SYMBOL", "(")
            inner = self._parse_expression()
            self._match("SYMBOL", ")")
            return inner

        # Initializer lists: { expr1, expr2, ... }
        if tok.type == "SYMBOL" and tok.value == "{":
            lbrace = self._match("SYMBOL", "{")
            elements = []
            if not (self._cur() and self._cur().type == "SYMBOL" and self._cur().value == "}"):
                elements.append(self._parse_expression())
                while self._cur() and self._cur().type == "SYMBOL" and self._cur().value == ",":
                    self._advance()
                    elements.append(self._parse_expression())
            self._match("SYMBOL", "}")
            node = ASTNode("InitializerList", line=lbrace.line)
            for el in elements:
                node.add_child(el)
            return node

        # Unary operators: -x, !x, etc.
        if tok.type == "OPERATOR" and tok.value in ("-", "!", "~", "&", "*", "++", "--"):
            op = self._match("OPERATOR")
            operand = self._parse_term()
            node = binary_op_node(f"unary{op.value}")
            node.add_child(operand)
            return node

        if tok.type == "IDENTIFIER":
            ident = self._match("IDENTIFIER")

            # Postfix unary operators: x++, x--
            if self._cur() and self._cur().type == "OPERATOR" and self._cur().value in ("++", "--"):
                op = self._match("OPERATOR")
                node = binary_op_node(f"unary{op.value}", line=ident.line)
                node.add_child(identifier_node(ident.value, line=ident.line))
                return node
            # Function calls: foo(arg1, arg2)
            if self._cur() and self._cur().type == "SYMBOL" and self._cur().value == "(":
                self._match("SYMBOL", "(")
                args = []
                if not (self._cur() and self._cur().type == "SYMBOL" and self._cur().value == ")"):
                    args.append(self._parse_expression())
                    while self._cur() and self._cur().type == "SYMBOL" and self._cur().value == ",":
                        self._advance()
                        args.append(self._parse_expression())
                self._match("SYMBOL", ")")
                call = call_expression_node(ident.value, line=ident.line)
                for arg in args:
                    call.add_child(arg)
                return call

            # Simple array index subscript: arr[index]
            if self._cur() and self._cur().type == "SYMBOL" and self._cur().value == "[":
                self._advance()
                self._parse_expression()
                if self._cur() and self._cur().value == "]":
                    self._advance()

            return identifier_node(ident.value, line=ident.line)

        if tok.type == "NUMBER":
            num = self._match("NUMBER")
            try:
                val = int(num.value, 0)
            except ValueError:
                val = float(num.value)
            return number_node(val, line=num.line)

        if tok.type in ("STRING", "CHAR"):
            s = self._match()
            node = string_node(s.value, line=s.line)
            node.meta["literal_type"] = "char" if tok.type == "CHAR" else "string"
            return node

        raise ParseError(f"Expected expression, got '{tok.value}'", tok.line)


def parse(tokens: List[Token]) -> ASTNode:
    return Parser(tokens).parse()
