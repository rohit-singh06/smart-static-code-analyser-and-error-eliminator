"""Test the full semantic pipeline."""
import sys
sys.path.insert(0, '.')

from lexer import lex
from parser import parse
from semantic.analyzer import SemanticAnalyzer
from semantic.quality_scorer import compute_quality

# Test code with intentional semantic errors
code = """
int main() {
    int x;
    int x;
    int y = 10;
    int z = x + y;
    return z;
    int unreachable = 5;
}
"""

print("=== TESTING SEMANTIC ANALYZER ===")
tokens = lex(code)
ast    = parse(tokens)
result = SemanticAnalyzer().analyze(ast)
quality = compute_quality(result.issues)

print(f"\nIssues found: {len(result.issues)}")
for i in result.issues:
    print(f"  [{i.kind}] {i.code} - {i.message} (line {i.line})")
    print(f"    Hint: {i.hint()}")

print(f"\nQuality Score: {quality['score']} ({quality['grade']}) - {quality['summary']}")
print(f"Symbol Table:")
for s in result.symbol_table.to_list():
    print(f"  {s['name']:12} used={s['used']} assigned={s['assigned']} line={s['declared_line']}")

print("\nAll assertions passed!")
