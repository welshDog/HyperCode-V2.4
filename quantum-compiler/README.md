# Quantum Compiler — HyperCode Experimental

> **What it does:** Compiles Brainfuck source code into executable Qiskit quantum circuits.

---

## The idea

Every Brainfuck instruction (`+`, `-`, `>`, `<`, `[`, `]`, `.`, `,`) maps to a quantum gate operation on a qubit register via IBM's Qiskit framework. The compiler generates Python code that runs on real quantum hardware or a local Qiskit simulator.

This is a frontier experiment — classical esoteric computing meets quantum circuit design.

---

## Status

**Experimental.** Works as a proof-of-concept transpiler. Not yet integrated into the main HyperCode agent pipeline.

- Go HTTP server (`main.go`) — accepts `POST /compile` with Brainfuck source, returns generated Qiskit Python
- JavaScript server (`server.js`) — alternative Node.js entrypoint
- Web UI (`index.html`) — browser-based compiler interface

---

## Run it

```bash
# Go server
go run main.go
# → listens on :8090

# Send a compile request
curl -X POST http://localhost:8090/compile \
  -H "Content-Type: application/json" \
  -d '{"code": "++>++<[->+<]"}'
```

Or open `index.html` in a browser for the visual interface.

---

## Output example

Input Brainfuck: `+`

Output (Qiskit Python):
```python
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister

qr = QuantumRegister(8)
cr = ClassicalRegister(8)
qc = QuantumCircuit(qr, cr)

qc.rx(math.pi / 8, qr[0])  # BF '+' → rotation gate
```

---

## Run tests

```bash
go test ./...
go test -bench=. ./...
```

---

## Requirements

- Go 1.21+
- Python 3.10+ with `qiskit` installed (`pip install qiskit`) to execute generated circuits
- IBM Quantum account (optional) for real hardware execution

---

## Roadmap

- [ ] Wire into agent-x as a code generation target
- [ ] Add more esoteric language frontends (Malbolge, Whitespace)
- [ ] Qiskit simulation output (run circuits locally without IBM account)
- [ ] Docker container for isolated compilation
