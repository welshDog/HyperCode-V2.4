## 1️⃣ THE-HYPERCODE: `docs/LANGUAGE_SPEC_v0.1.md`

**Path:** `THE-HYPERCODE/docs/LANGUAGE_SPEC_v0.1.md`

```markdown
# HyperCode Language Specification v0.1

> **Goal:** Ship a usable, Python-like core language THIS WEEK that we can evolve into full ND/visual HyperCode later.

---

## 1. Design Principles

1. **Neurodivergent-first**
   - Minimize cognitive load (simple, predictable rules)
   - Prefer explicit over “magic”
   - Friendly, conversational errors

2. **Python-familiar**
   - Anyone who knows basic Python can read/write HyperCode v0.1
   - This lets us ship fast and onboard collaborators

3. **Future-proof**
   - AST-first design so we can later:
     - Add ND/emoji sugar that compiles to same AST
     - Target Rust / Mojo / Quantum / Molecular backends

---

## 2. Core Syntax (v0.1)

### 2.1 Files and Modules

- File extension: `.hc`
- One module per file
- Top-level code is allowed (like Python)

```hypercode
# example.hc
print("Hello HyperCode! 🧠🚀")
```

---

### 2.2 Comments

- Single-line comments start with `#`
- No block comments (yet)

```hypercode
# This is a comment
x = 42  # inline comment
```

---

### 2.3 Values and Types

Supported primitive types in v0.1:

- `int`
- `float`
- `str`
- `bool`
- `list`
- `dict`
- `None`

```hypercode
name = "Lyndz"
age = 30
pi = 3.14159
is_hyperfocused = True
numbers = [github](https://github.com/welshDog/HyperCode-V2.0)
profile = {"name": name, "age": age}
nothing = None
```

Type hints are **optional**, but recommended for clarity:

```hypercode
name: str = "Lyndz"
age: int = 30
pi: float = 3.14159
```

---

### 2.4 Variables

- Assignment with `=`
- Re-assignment allowed (like Python)
- No `var` / `let` keywords in v0.1

```hypercode
count = 0
count = count + 1
```

---

### 2.5 Expressions

Supported:

- Arithmetic: `+`, `-`, `*`, `/`, `//`, `%`, `**`
- Comparison: `==`, `!=`, `<`, `<=`, `>`, `>=`
- Boolean: `and`, `or`, `not`

```hypercode
score = (10 + 5) * 2 / 3
is_adult = age >= 18 and age < 120
```

---

### 2.6 Functions

```hypercode
def greet(name):
    print("Hey " + name + ", BRO! 👊")

def add(a: int, b: int) -> int:
    result = a + b
    return result

total = add(5, 7)
greet("Lyndz")
```

Rules:

- Functions defined with `def`
- Optional return type annotation using `->`
- `return` ends the function

---

### 2.7 Conditionals

```hypercode
if age >= 18:
    print("Adult")
elif age >= 13:
    print("Teenager")
else:
    print("Child")
```

Rules:

- `if`, optional `elif`, optional `else`
- Indentation is 4 spaces (hard rule in v0.1)

---

### 2.8 Loops

#### `for` loop (iterating sequences)

```hypercode
for num in: [dl.acm](https://dl.acm.org/doi/10.1145/3719027.3767672)
    print(num)

items = ["code", "rest", "play"]
for item in items:
    print("Today:", item)
```

#### `while` loop

```hypercode
count = 3
while count > 0:
    print("Countdown:", count)
    count = count - 1
```

---

### 2.9 Built‑in Functions (v0.1)

We support a tiny, safe subset:

- `print(value)`
- `len(sequence)`
- `range(stop)` / `range(start, stop[, step])`

```hypercode
print("Hello")
print(len()) [canada](https://www.canada.ca/content/dam/phac-aspc/documents/services/reports-publications/canada-communicable-disease-report-ccdr/monthly-issue/2025-51/issue-9-september-2025/ccdrv51i09a01-eng.pdf)

for i in range(5):
    print(i)
```

---

## 3. Example Programs

### 3.1 Hello World

```hypercode
# hello_world.hc
print("Hello, HyperCode! 🧠🚀")
```

---

### 3.2 Arithmetic

```hypercode
# arithmetic.hc
a = 10
b = 5

sum_value = a + b
diff = a - b
product = a * b
quotient = a / b

print("Sum:", sum_value)
print("Diff:", diff)
print("Product:", product)
print("Quotient:", quotient)
```

---

### 3.3 Function

```hypercode
# function.hc
def add(a, b):
    return a + b

result = add(15, 27)
print("Result:", result)
```

---

### 3.4 Conditional

```hypercode
# conditional.hc
age = 25

if age >= 18:
    print("Adult")
else:
    print("Minor")
```

---

### 3.5 Loop

```hypercode
# loop.hc
for num in: [ejournal.nusantaraglobal.ac](https://ejournal.nusantaraglobal.ac.id/index.php/sentri/article/view/4534)
    print("Number:", num)
```

---

## 4. Future Extensions (v0.2+)

These are **NOT** required for v0.1, but we’re designing around them.

### 4.1 ND/Emoji Sugar

```hypercode
🎯 goal add_numbers:
    📊 inputs:
        a (number)
        b (number)

    🧮 process:
        result = a + b

    ✅ return result
```

…will compile to the same AST as:

```hypercode
def add_numbers(a, b):
    result = a + b
    return result
```

### 4.2 Quantum Mode (Sketch)

```hypercode
@quantum
def bell_state():
    q0 = qubit()
    q1 = qubit()
    H(q0)
    CNOT(q0, q1)
    return measure(q0, q1)
```

### 4.3 Molecular Mode (Sketch)

```hypercode
@molecular
def dna_cascade(A, B, C, D):
    return Cascade(domain=A, toehold=B, strand=C, output=D)
```

---

## 5. Non‑Goals for v0.1

To ship fast, v0.1 **does NOT** include:

- Classes / OOP
- Exceptions
- Imports / modules
- Async / await
- Comprehensions
- Decorators (other than reserved `@quantum`, `@molecular` keywords)

We can add these incrementally once v0.1 is stable.

---

## 6. Summary

- v0.1 is **Python‑lite** with strict, simple rules.
- It’s enough to:
  - Parse
  - Build an AST
  - Run via a Python backend
  - Later compile to Rust/Mojo/Quantum/DNA.

Ship this first.
Then wrap the wild ND syntax on top.
```

***

## 2️⃣ THE-HYPERCODE: Tiny Parser Skeleton

**Path:** `THE-HYPERCODE/hypercode-core/app/parser/hc_parser.py`

> This is intentionally minimal – just enough structure to start building tests and a real parser later.

```python
# hypercode-core/app/parser/hc_parser.py

"""
HyperCode v0.1 Parser Skeleton

Goal:
- Provide a clean entrypoint: `parse(code: str) -> AST`
- Wrap Python's `ast` module for v0.1
- Later: replace with our own full parser.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, List, Optional
import ast


# --- Simple AST Wrapper -----------------------------------------------------


@dataclass
class HCNode:
    kind: str
    value: Any = None
    children: List["HCNode"] = None
    lineno: Optional[int] = None
    col_offset: Optional[int] = None

    def __post_init__(self):
        if self.children is None:
            self.children = []


@dataclass
class HCProgram:
    body: List[HCNode]


# --- Public API -------------------------------------------------------------


def parse(code: str) -> HCProgram:
    """
    Parse HyperCode v0.1 source into a simple AST wrapper.

    For v0.1:
    - We lean on Python's `ast` parser
    - Then map Python AST → HCNode tree
    """
    py_ast = ast.parse(code)
    return HCProgram(body=[_convert_node(n) for n in py_ast.body])


# --- Internal Conversion Helpers -------------------------------------------


def _convert_node(node: ast.AST) -> HCNode:
    if isinstance(node, ast.Expr):
        return HCNode(
            kind="expr",
            value=_repr_expr(node.value),
            lineno=getattr(node, "lineno", None),
            col_offset=getattr(node, "col_offset", None),
        )

    if isinstance(node, ast.Assign):
        return HCNode(
            kind="assign",
            value={
                "targets": [_repr_expr(t) for t in node.targets],
                "value": _repr_expr(node.value),
            },
            lineno=node.lineno,
            col_offset=node.col_offset,
        )

    if isinstance(node, ast.FunctionDef):
        return HCNode(
            kind="function_def",
            value={
                "name": node.name,
                "args": [arg.arg for arg in node.args.args],
                "returns": _repr_type(node.returns),
            },
            children=[_convert_node(stmt) for stmt in node.body],
            lineno=node.lineno,
            col_offset=node.col_offset,
        )

    if isinstance(node, ast.If):
        return HCNode(
            kind="if",
            value={"test": _repr_expr(node.test)},
            children=[_convert_node(stmt) for stmt in node.body],
            lineno=node.lineno,
            col_offset=node.col_offset,
        )

    if isinstance(node, ast.For):
        return HCNode(
            kind="for",
            value={
                "target": _repr_expr(node.target),
                "iter": _repr_expr(node.iter),
            },
            children=[_convert_node(stmt) for stmt in node.body],
            lineno=node.lineno,
            col_offset=node.col_offset,
        )

    if isinstance(node, ast.While):
        return HCNode(
            kind="while",
            value={"test": _repr_expr(node.test)},
            children=[_convert_node(stmt) for stmt in node.body],
            lineno=node.lineno,
            col_offset=node.col_offset,
        )

    # Fallback: generic representation
    return HCNode(
        kind=type(node).__name__,
        value=ast.dump(node),
        lineno=getattr(node, "lineno", None),
        col_offset=getattr(node, "col_offset", None),
    )


def _repr_expr(node: ast.AST) -> Any:
    """Small helper to get a readable representation of expressions for v0.1."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return {"var": node.id}
    if isinstance(node, ast.BinOp):
        return {
            "binop": {
                "left": _repr_expr(node.left),
                "op": type(node.op).__name__,
                "right": _repr_expr(node.right),
            }
        }
    if isinstance(node, ast.Call):
        return {
            "call": {
                "func": _repr_expr(node.func),
                "args": [_repr_expr(a) for a in node.args],
            }
        }
    return ast.dump(node)


def _repr_type(node: Optional[ast.expr]) -> Optional[str]:
    if node is None:
        return None
    if isinstance(node, ast.Name):
        return node.id
    return ast.dump(node)
```

***

## 3️⃣ THE-HYPERCODE: Parser Test File

**Path:** `THE-HYPERCODE/hypercode-core/tests/test_parser.py`

```python
# hypercode-core/tests/test_parser.py

from app.parser.hc_parser import parse, HCProgram, HCNode


def test_parse_hello_world():
    code = 'print("Hello, HyperCode! 🧠🚀")\n'
    program = parse(code)

    assert isinstance(program, HCProgram)
    assert len(program.body) == 1
    node = program.body[0]
    assert node.kind == "expr"
    assert "call" in str(node.value)


def test_parse_assignment():
    code = "x = 42\n"
    program = parse(code)

    assert len(program.body) == 1
    node = program.body[0]
    assert node.kind == "assign"
    assert node.value["targets"][0]["var"] == "x"
    assert node.value["value"] == 42


def test_parse_function_def():
    code = """
def add(a, b):
    return a + b
"""
    program = parse(code)
    node = program.body[0]

    assert node.kind == "function_def"
    assert node.value["name"] == "add"
    assert node.value["args"] == ["a", "b"]
    assert node.children  # body not empty
```

***

## 4️⃣ HyperCode-V2.0: Simple Engine Proxy

**Path:** `HyperCode-V2.0/api/engine_client.py` (or similar FastAPI service)

```python
# api/engine_client.py

import httpx
from typing import Literal

ENGINE_URL = "http://hypercode-engine:8001"


async def execute_hypercode(
    code: str,
    target: Literal["python", "rust", "mojo"] = "python",
):
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{ENGINE_URL}/execute",
            json={"code": code, "target": target},
        )
    resp.raise_for_status()
    return resp.json()
```

***

which repo you want to touch first (V2.0 vs THE-HYPERCODE), you can:

- turn these into **exact file trees** for your structure,  
- or write the **FastAPI `POST /execute`** handler on the core side next.
