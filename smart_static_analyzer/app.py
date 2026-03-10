"""
Flask backend for the Smart Static Code Analyzer (Phase 1 - 40%).

Pipeline:
    Source code → Lexer → Parser → AST → JSON response
"""

from __future__ import annotations

from flask import Flask, render_template, request, jsonify

from .lexer import lex, LexicalError
from .parser import parse, ParseError
from .utils import ast_to_dict, tokens_to_list


app = Flask(__name__, template_folder="templates", static_folder="static")


@app.route("/", methods=["GET"])
def index():
    """Serve the main analysis page."""
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze_code():
    """
    Analyze source code sent as JSON:
        { "code": "int x; x = 10; return;" }
    Returns tokens and AST or error messages.
    """
    data = request.get_json(silent=True) or {}
    source = data.get("code", "")

    if not isinstance(source, str):
        return jsonify({"error": "Field 'code' must be a string."}), 400

    try:
        tokens = lex(source)
        ast_root = parse(tokens)
        return jsonify(
            {
                "tokens": tokens_to_list(tokens),
                "ast": ast_to_dict(ast_root),
                "errors": [],
            }
        )
    except LexicalError as le:
        return jsonify({"tokens": [], "ast": None, "errors": [str(le)]}), 400
    except ParseError as pe:
        return jsonify({"tokens": tokens_to_list(lex(source)), "ast": None, "errors": [str(pe)]}), 400
    except Exception as e:
        # Fallback for unexpected errors
        return jsonify({"tokens": [], "ast": None, "errors": [f"Internal error: {e}"]}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)

