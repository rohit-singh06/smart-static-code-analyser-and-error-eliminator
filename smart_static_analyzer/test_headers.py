from lexer import lex
from parser import parse
from utils import ast_to_dict

code = """#include <stdio.h>
#include <stdlib.h>

// Entry point comment
int main() {
    int x = 10;
    int y = x + 5;
    /* block comment */
    printf("Hello!");
    return 0;
}"""

print("=== TOKENS ===")
tokens = lex(code)
for t in tokens:
    print(f"  {t.type:15} {t.value!r:25} line {t.line}")

print("\n=== PARSE ===")
ast = parse(tokens)
print("AST root:", ast.type)
for c in ast.children:
    print("  child:", c.type, c.value)
    for gc in c.children:
        print("    grandchild:", gc.type, gc.value)

print("\nAll OK!")
