"""
Flask Web Server — Static Code Analyzer.
"""

from collections import deque, Counter
from datetime import datetime
from flask import Flask, render_template, request, jsonify

from lexer import lex, LexicalError
from parser import parse, ParseError
from utils import ast_to_dict, tokens_to_list
from compiler.compile_checker import check_with_gcc
from analyzer.ast_parser import parse_with_pycparser
from semantic.analyzer import SemanticAnalyzer
from semantic.quality_scorer import compute_quality

app = Flask(__name__, template_folder="templates", static_folder="static")

history = deque(maxlen=20)


def compute_metrics(tokens, ast_root) -> dict:
    """Extract general code and AST structure metrics."""
    counts = Counter(t.type for t in tokens)
    variables = []
    functions = []

    def walk(node) -> int:
        if node is None:
            return 0
        if node.type == "Declaration" and node.value and node.value not in variables:
            variables.append(node.value)
        elif node.type == "FunctionDef" and node.value and node.value not in functions:
            functions.append(node.value)

        depths = [walk(c) for c in node.children]
        return 1 + (max(depths) if depths else 0)

    depth = walk(ast_root) if ast_root else 0
    return {
        "token_counts": dict(counts),
        "total_tokens": len(tokens),
        "variables": variables,
        "functions": functions,
        "ast_depth": depth,
    }


def save_history(source: str, tokens: list, errors: list, gcc_ok: bool) -> None:
    history.appendleft({
        "timestamp": datetime.now().isoformat(),
        "source_preview": source[:100].replace("\n", " ↵ "),
        "token_count": len(tokens),
        "errors": errors,
        "gcc_ok": gcc_ok,
        "sem_errors": 0,
        "sem_warnings": 0,
        "quality_grade": "—",
    })


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True) or {}
    source = data.get("code", "")

    if not isinstance(source, str):
        return jsonify({"error": "Field 'code' must be a string."}), 400

    result = {
        "tokens": [], "ast": None, "gcc": None, "pycparser": None,
        "metrics": None, "semantic": None, "errors": [],
    }

    try:
        tokens = lex(source)
        ast_root = parse(tokens)

        gcc_res = check_with_gcc(source)
        pyc_res = parse_with_pycparser(source)
        metrics = compute_metrics(tokens, ast_root)

        sem_result = SemanticAnalyzer().analyze(ast_root)
        quality = compute_quality(sem_result.issues)
        sem_dict = sem_result.to_dict()
        sem_dict["quality"] = quality

        result.update({
            "tokens": tokens_to_list(tokens),
            "ast": ast_to_dict(ast_root),
            "gcc": gcc_res.to_dict(),
            "pycparser": pyc_res.to_dict(),
            "metrics": metrics,
            "semantic": sem_dict,
            "errors": [],
        })

        history.appendleft({
            "timestamp": datetime.now().isoformat(),
            "source_preview": source[:100].replace("\n", " ↵ "),
            "token_count": len(tokens),
            "errors": [],
            "gcc_ok": gcc_res.ok,
            "sem_errors": sem_dict["error_count"],
            "sem_warnings": sem_dict["warning_count"],
            "quality_grade": quality["grade"],
        })
        return jsonify(result)

    except LexicalError as le:
        gcc_res = check_with_gcc(source)
        pyc_res = parse_with_pycparser(source)
        result.update({
            "gcc": gcc_res.to_dict(),
            "pycparser": pyc_res.to_dict(),
            "errors": [str(le)],
        })
        save_history(source, [], [str(le)], False)
        return jsonify(result), 400

    except ParseError as pe:
        toks = []
        try:
            toks = tokens_to_list(lex(source))
        except Exception:
            pass
        gcc_res = check_with_gcc(source)
        pyc_res = parse_with_pycparser(source)
        
        msg = str(pe)
        qf = None
        if "Expected ';'" in msg:
            # We suggest inserting a semicolon at the end of the line
            qf = {
                "label": "Insert missing ';'",
                "action": "insert_semicolon",
                "line": pe.line
            }

        err_payload = {
            "message": msg,
            "line": pe.line,
            "quick_fix": qf
        }

        result.update({
            "tokens": toks,
            "gcc": gcc_res.to_dict(),
            "pycparser": pyc_res.to_dict(),
            "errors": [err_payload],
        })
        save_history(source, toks, [msg], False)
        return jsonify(result), 400

    except Exception as e:
        result["errors"] = [f"Internal error: {e}"]
        return jsonify(result), 500


@app.route("/history", methods=["GET"])
def get_history():
    return jsonify(list(history))


@app.route("/history/clear", methods=["POST"])
def clear_history():
    history.clear()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
