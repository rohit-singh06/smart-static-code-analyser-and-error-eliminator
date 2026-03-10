"""
Utility helpers for the Smart Static Code Analyzer.
"""

from __future__ import annotations

from typing import Any, List

from .ast_nodes import ASTNode
from .lexer import Token


def ast_to_dict(node: ASTNode) -> dict:
    """Convert an ASTNode tree into a JSON-serializable dict."""
    return {
        "type": node.type,
        "value": node.value,
        "children": [ast_to_dict(child) for child in node.children],
    }


def tokens_to_list(tokens: List[Token]) -> list[dict[str, Any]]:
    """Convert Token objects to simple dictionaries."""
    return [t.to_dict() for t in tokens]

