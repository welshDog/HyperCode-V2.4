// quantum-compiler/server.js - HyperCode Quantum Esoteric Compiler (Node.js)
const http = require('http');
const url = require('url');

function compileBF(source) {
  const quantum = [];
  quantum.push("from __future__ import annotations");
  quantum.push("");
  quantum.push("import math");
  quantum.push("");
  quantum.push("from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister");
  quantum.push("from qiskit.quantum_info import Statevector");
  quantum.push("");
  quantum.push("");
  quantum.push("def _bf_plus(qc: QuantumCircuit, qr: QuantumRegister, cr: ClassicalRegister) -> None:");
  quantum.push("    qc.rx(math.pi / 8, qr[0])");
  quantum.push("");
  quantum.push("");
  quantum.push("def _bf_minus(qc: QuantumCircuit, qr: QuantumRegister, cr: ClassicalRegister) -> None:");
  quantum.push("    qc.rx(-math.pi / 8, qr[0])");
  quantum.push("");
  quantum.push("");
  quantum.push("def _bf_move_right(qc: QuantumCircuit, qr: QuantumRegister, cr: ClassicalRegister) -> None:");
  quantum.push("    qc.swap(qr[0], qr[1])");
  quantum.push("");
  quantum.push("");
  quantum.push("def _bf_move_left(qc: QuantumCircuit, qr: QuantumRegister, cr: ClassicalRegister) -> None:");
  quantum.push("    qc.swap(qr[0], qr[1])");
  quantum.push("");
  quantum.push("");
  quantum.push("def _bf_output(qc: QuantumCircuit, qr: QuantumRegister, cr: ClassicalRegister) -> None:");
  quantum.push("    qc.measure(qr[0], cr[0])");
  quantum.push("");
  quantum.push("");
  quantum.push("def _bf_input(qc: QuantumCircuit, qr: QuantumRegister, cr: ClassicalRegister) -> None:");
  quantum.push("    qc.h(qr[0])");
  quantum.push("");
  quantum.push("");
  quantum.push("def _bf_loop_start(qc: QuantumCircuit, qr: QuantumRegister, cr: ClassicalRegister) -> None:");
  quantum.push("    return");
  quantum.push("");
  quantum.push("");
  quantum.push("def _bf_loop_end(qc: QuantumCircuit, qr: QuantumRegister, cr: ClassicalRegister) -> None:");
  quantum.push("    return");
  quantum.push("");
  quantum.push("");
  quantum.push("_INSTR = {");
  quantum.push("    '+': _bf_plus,");
  quantum.push("    '-': _bf_minus,");
  quantum.push("    '>': _bf_move_right,");
  quantum.push("    '<': _bf_move_left,");
  quantum.push("    '.': _bf_output,");
  quantum.push("    ',': _bf_input,");
  quantum.push("    '[': _bf_loop_start,");
  quantum.push("    ']': _bf_loop_end,");
  quantum.push("}");
  quantum.push("");
  quantum.push("");
  quantum.push("def build_circuit(source: str) -> QuantumCircuit:");
  quantum.push("    qr = QuantumRegister(2, 'q')");
  quantum.push("    cr = ClassicalRegister(2, 'c')");
  quantum.push("    qc = QuantumCircuit(qr, cr, name='brainfuck_compiled')");
  quantum.push("");
  quantum.push("    for ch in source:");
  quantum.push("        fn = _INSTR.get(ch)");
  quantum.push("        if fn is not None:");
  quantum.push("            fn(qc, qr, cr)");
  quantum.push("");
  quantum.push("    qc.measure(qr, cr)");
  quantum.push("    return qc");
  quantum.push("");
  quantum.push("");
  quantum.push("if __name__ == '__main__':");
  quantum.push(`    SOURCE = ${JSON.stringify(source)}`);
  quantum.push("    circuit = build_circuit(SOURCE)");
  quantum.push("    state = Statevector.from_instruction(");
  quantum.push("        circuit.remove_final_measurements(inplace=False)");
  quantum.push("    )");
  quantum.push("    print(state)");

  return quantum.join("\n");
}

const server = http.createServer((req, res) => {
  const parsedUrl = url.parse(req.url, true);
  const pathname = parsedUrl.pathname;
  const method = req.method;

  // Set CORS headers
  res.setHeader('Content-Type', 'application/json');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  // Health check endpoint
  if (pathname === '/quantum-compiler/health') {
    res.writeHead(200);
    res.end(JSON.stringify({
      status: 'healthy',
      service: 'quantum-compiler',
      version: '1.0.0'
    }, null, 2));
    return;
  }

  // Compile endpoint
  if (pathname === '/quantum-compiler/compile') {
    let bfCode = '';

    if (method === 'POST') {
      let body = '';
      req.on('data', chunk => body += chunk);
      req.on('end', () => {
        try {
          const data = JSON.parse(body);
          bfCode = data.code || '';
        } catch (e) {
          res.writeHead(400);
          res.end(JSON.stringify({
            success: false,
            message: 'Invalid JSON: ' + e.message
          }, null, 2));
          return;
        }
        handleCompile(bfCode, res);
      });
      return;
    } else {
      // GET request
      bfCode = parsedUrl.query.code || '';
      handleCompile(bfCode, res);
      return;
    }
  }

  // Root endpoint
  if (pathname === '/') {
    res.writeHead(200);
    res.end(JSON.stringify({
      service: 'HyperCode Quantum Esoteric Compiler',
      version: '1.0.0',
      endpoints: [
        '/quantum-compiler/compile - Compile Brainfuck to Qiskit',
        '/quantum-compiler/health  - Health check'
      ],
      usage: 'POST /quantum-compiler/compile with JSON body: {"code": "++++[>++<-]"}'
    }, null, 2));
    return;
  }

  // 404 for unknown paths
  res.writeHead(404);
  res.end(JSON.stringify({
    success: false,
    message: 'Not found'
  }, null, 2));
});

function handleCompile(bfCode, res) {
  if (!bfCode) {
    res.writeHead(400);
    res.end(JSON.stringify({
      success: false,
      message: "No Brainfuck code provided. Use 'code' parameter."
    }, null, 2));
    return;
  }

  const qCode = compileBF(bfCode);
  
  res.writeHead(200);
  res.end(JSON.stringify({
    success: true,
    quantum_code: qCode,
    message: 'Compilation successful'
  }, null, 2));
}

const PORT = 8081;
server.listen(PORT, () => {
  console.log(`🚀 Quantum Compiler starting on http://localhost:${PORT}`);
  console.log(`📡 Endpoints:`);
  console.log(`   - POST/GET /quantum-compiler/compile?code=<brainfuck>`);
  console.log(`   - GET /quantum-compiler/health`);
  console.log(`\n🧪 Test: curl "http://localhost:${PORT}/quantum-compiler/compile?code=++++[>++<-]"`);
});
