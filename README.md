# Smart Static Code Analyzer

A simple **C-like language** static analyzer implemented in Python + Flask.

This phase covers:

- Source code input UI
- Flask backend
- Lexer (tokenizer)
- Recursive descent parser
- AST (abstract syntax tree) generation and display

## Project Structure

```text
smart_static_analyzer/
│
├── app.py          # Flask backend, /analyze endpoint
├── lexer.py        # Lexer (tokenizer)
├── parser.py       # Recursive descent parser
├── ast_nodes.py    # AST node model
├── utils.py        # Converters for tokens/AST → JSON
│
├── templates/
│   └── index.html  # Web UI
│
└── static/
    └── style.css   # Styles for UI
```

## Language Subset (Supported)

- Variable declaration:

  ```c
  int x;
  ```

- Assignment:

  ```c
  x = 10;
  x = y + 2;
  ```

- Return statement:

  ```c
  return;
  ```

- Block scope:

  ```c
  {
      int x;
      x = 10;
  }
  ```

## Grammar

```text
Program        → StatementList
StatementList  → Statement StatementList | ε

Statement      → Declaration
               → Assignment
               → ReturnStatement
               → Block

Declaration    → 'int' IDENTIFIER ';'
Assignment     → IDENTIFIER '=' Expression ';'
ReturnStatement→ 'return' ';'
Block          → '{' StatementList '}'

Expression     → Term ((+ | -) Term)*
Term           → IDENTIFIER | NUMBER
```

## Running the App

```bash
cd smart_static_analyzer
pip install flask
python app.py
```

Then open `http://127.0.0.1:5000` in your browser.

## API Endpoint

- **POST** `/analyze`

Request body:

```json
{
  "code": "int x; x = 10; return;"
}
```

Response body:

```json
{
  "tokens": [ ... ],
  "ast": { ... },
  "errors": []
}
```

If lexical or syntax errors are detected, they are returned in the `errors` array and `ast` will be `null`.

# Contributrd by Nush
