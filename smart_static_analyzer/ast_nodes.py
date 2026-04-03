"""
AST node definitions for the Smart Static Code Analyzer.
Each node has: type, value, children, line.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Any


@dataclass
class ASTNode:
    type: str
    value: Any | None = None
    children: List["ASTNode"] = field(default_factory=list)
    line: int = 0

    def add_child(self, child: "ASTNode") -> None:
        self.children.append(child)


def program_node(children: List[ASTNode]) -> ASTNode:
    return ASTNode(type="Program", children=children)

def declaration_node(name: str, line: int = 0) -> ASTNode:
    return ASTNode(type="Declaration", value=name, line=line)

def assignment_node(line: int = 0) -> ASTNode:
    return ASTNode(type="Assignment", line=line)

def return_node(line: int = 0) -> ASTNode:
    return ASTNode(type="Return", line=line)

def block_node(children: List[ASTNode], line: int = 0) -> ASTNode:
    return ASTNode(type="Block", children=children, line=line)

def binary_op_node(op: str, line: int = 0) -> ASTNode:
    return ASTNode(type="BinaryOp", value=op, line=line)

def identifier_node(name: str, line: int = 0) -> ASTNode:
    return ASTNode(type="Identifier", value=name, line=line)

def number_node(value: int, line: int = 0) -> ASTNode:
    return ASTNode(type="Number", value=value, line=line)

def string_node(value: str, line: int = 0) -> ASTNode:
    return ASTNode(type="String", value=value, line=line)

def function_def_node(name: str, line: int = 0) -> ASTNode:
    return ASTNode(type="FunctionDef", value=name, line=line)

def expression_stmt_node(expr: ASTNode, line: int = 0) -> ASTNode:
    node = ASTNode(type="ExpressionStatement", line=line)
    node.add_child(expr)
    return node

def call_expression_node(callee: str, line: int = 0) -> ASTNode:
    return ASTNode(type="CallExpression", value=callee, line=line)
