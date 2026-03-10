"""
AST node definitions for the Smart Static Code Analyzer.

Each node has:
    - type:   string name of the node kind
    - value:  optional payload (e.g. identifier name, operator symbol)
    - children: list of child nodes
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Any


@dataclass
class ASTNode:
    """Base AST node type."""

    type: str
    value: Any | None = None
    children: List["ASTNode"] = field(default_factory=list)

    def add_child(self, child: "ASTNode") -> None:
        self.children.append(child)


def program_node(children: List[ASTNode]) -> ASTNode:
    return ASTNode(type="Program", value=None, children=children)


def declaration_node(name: str) -> ASTNode:
    """Variable declaration; optional initializer expression can be attached as a child."""
    return ASTNode(type="Declaration", value=name)


def assignment_node() -> ASTNode:
    return ASTNode(type="Assignment")


def return_node() -> ASTNode:
    return ASTNode(type="Return")


def block_node(children: List[ASTNode]) -> ASTNode:
    return ASTNode(type="Block", children=children)


def binary_op_node(op: str) -> ASTNode:
    return ASTNode(type="BinaryOp", value=op)


def identifier_node(name: str) -> ASTNode:
    return ASTNode(type="Identifier", value=name)


def number_node(value: int) -> ASTNode:
    return ASTNode(type="Number", value=value)


def function_def_node(name: str) -> ASTNode:
    """Function definition node; body block is attached as a child."""
    return ASTNode(type="FunctionDef", value=name)


def expression_stmt_node(expr: ASTNode) -> ASTNode:
    """Wrap an expression used as a statement (e.g., function call)."""
    node = ASTNode(type="ExpressionStatement")
    node.add_child(expr)
    return node


def call_expression_node(callee: str) -> ASTNode:
    """Function call expression; arguments are attached as children."""
    return ASTNode(type="CallExpression", value=callee)

