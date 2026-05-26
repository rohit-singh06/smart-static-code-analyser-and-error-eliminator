"""
AST node definitions for the Static Code Analyzer.
"""

class ASTNode:
    def __init__(self, type: str, value=None, children=None, line: int = 0, meta=None):
        self.type = type
        self.value = value
        self.children = children or []
        self.line = line
        self.meta = meta or {}

    def add_child(self, child: "ASTNode") -> None:
        self.children.append(child)


# Helper functions to build AST nodes
def program_node(children) -> ASTNode:
    return ASTNode("Program", children=children)

def declaration_node(name: str, line: int = 0) -> ASTNode:
    return ASTNode("Declaration", value=name, line=line)

def assignment_node(line: int = 0) -> ASTNode:
    return ASTNode("Assignment", line=line)

def return_node(line: int = 0) -> ASTNode:
    return ASTNode("Return", line=line)

def block_node(children, line: int = 0) -> ASTNode:
    return ASTNode("Block", children=children, line=line)

def binary_op_node(op: str, line: int = 0) -> ASTNode:
    return ASTNode("BinaryOp", value=op, line=line)

def identifier_node(name: str, line: int = 0) -> ASTNode:
    return ASTNode("Identifier", value=name, line=line)

def number_node(value, line: int = 0) -> ASTNode:
    return ASTNode("Number", value=value, line=line)

def string_node(value: str, line: int = 0) -> ASTNode:
    return ASTNode("String", value=value, line=line)

def function_def_node(name: str, line: int = 0) -> ASTNode:
    return ASTNode("FunctionDef", value=name, line=line)

def expression_stmt_node(expr: ASTNode, line: int = 0) -> ASTNode:
    node = ASTNode("ExpressionStatement", line=line)
    node.add_child(expr)
    return node

def call_expression_node(callee: str, line: int = 0) -> ASTNode:
    return ASTNode("CallExpression", value=callee, line=line)
