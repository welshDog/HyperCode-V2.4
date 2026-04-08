// quantum-compiler/main.go - HyperCode Quantum Esoteric Compiler
package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"strings"
)

// CompileRequest represents the incoming compilation request
type CompileRequest struct {
	Code string `json:"code"`
}

// CompileResponse represents the compilation result
type CompileResponse struct {
	Success    bool   `json:"success"`
	QuantumCode string `json:"quantum_code"`
	Message    string `json:"message,omitempty"`
}

func compileBF(source string) string {
	sourceLiteral := strconv.Quote(source)

	lines := []string{
		"from __future__ import annotations",
		"",
		"import math",
		"",
		"from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister",
		"from qiskit.quantum_info import Statevector",
		"",
		"",
		"def _bf_plus(qc: QuantumCircuit, qr: QuantumRegister, cr: ClassicalRegister) -> None:",
		"    qc.rx(math.pi / 8, qr[0])",
		"",
		"",
		"def _bf_minus(qc: QuantumCircuit, qr: QuantumRegister, cr: ClassicalRegister) -> None:",
		"    qc.rx(-math.pi / 8, qr[0])",
		"",
		"",
		"def _bf_move_right(qc: QuantumCircuit, qr: QuantumRegister, cr: ClassicalRegister) -> None:",
		"    qc.swap(qr[0], qr[1])",
		"",
		"",
		"def _bf_move_left(qc: QuantumCircuit, qr: QuantumRegister, cr: ClassicalRegister) -> None:",
		"    qc.swap(qr[0], qr[1])",
		"",
		"",
		"def _bf_output(qc: QuantumCircuit, qr: QuantumRegister, cr: ClassicalRegister) -> None:",
		"    qc.measure(qr[0], cr[0])",
		"",
		"",
		"def _bf_input(qc: QuantumCircuit, qr: QuantumRegister, cr: ClassicalRegister) -> None:",
		"    qc.h(qr[0])",
		"",
		"",
		"def _bf_loop_start(qc: QuantumCircuit, qr: QuantumRegister, cr: ClassicalRegister) -> None:",
		"    return",
		"",
		"",
		"def _bf_loop_end(qc: QuantumCircuit, qr: QuantumRegister, cr: ClassicalRegister) -> None:",
		"    return",
		"",
		"",
		"_INSTR = {",
		"    '+': _bf_plus,",
		"    '-': _bf_minus,",
		"    '>': _bf_move_right,",
		"    '<': _bf_move_left,",
		"    '.': _bf_output,",
		"    ',': _bf_input,",
		"    '[': _bf_loop_start,",
		"    ']': _bf_loop_end,",
		"}",
		"",
		"",
		"def build_circuit(source: str) -> QuantumCircuit:",
		"    qr = QuantumRegister(2, 'q')",
		"    cr = ClassicalRegister(2, 'c')",
		"    qc = QuantumCircuit(qr, cr, name='brainfuck_compiled')",
		"",
		"    for ch in source:",
		"        fn = _INSTR.get(ch)",
		"        if fn is not None:",
		"            fn(qc, qr, cr)",
		"",
		"    qc.measure(qr, cr)",
		"    return qc",
		"",
		"",
		"if __name__ == '__main__':",
		"    SOURCE = " + sourceLiteral,
		"    circuit = build_circuit(SOURCE)",
		"    state = Statevector.from_instruction(",
		"        circuit.remove_final_measurements(inplace=False)",
		"    )",
		"    print(state)",
	}

	return strings.Join(lines, "\n")
}

func compileHandler(w http.ResponseWriter, r *http.Request) {
	accept := r.Header.Get("Accept")
	if strings.Contains(accept, "text/x-python") || r.URL.Query().Get("raw") == "1" {
		w.Header().Set("Content-Type", "text/x-python; charset=utf-8")
	} else {
		w.Header().Set("Content-Type", "application/json")
	}
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type")

	if r.Method == "OPTIONS" {
		w.WriteHeader(http.StatusOK)
		return
	}

	var bfCode string

	if r.Method == "POST" {
		var req CompileRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			json.NewEncoder(w).Encode(CompileResponse{
				Success: false,
				Message: "Invalid JSON: " + err.Error(),
			})
			return
		}
		bfCode = req.Code
	} else {
		// GET request - read from query parameter
		bfCode = r.URL.Query().Get("code")
	}

	if bfCode == "" {
		json.NewEncoder(w).Encode(CompileResponse{
			Success: false,
			Message: "No Brainfuck code provided. Use 'code' parameter.",
		})
		return
	}

	qCode := compileBF(bfCode)

	if strings.Contains(w.Header().Get("Content-Type"), "text/x-python") {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(qCode))
		return
	}

	_ = json.NewEncoder(w).Encode(CompileResponse{
		Success:     true,
		QuantumCode: qCode,
		Message:     "Compilation successful",
	})
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{
		"status":  "healthy",
		"service": "quantum-compiler",
		"version": "1.0.0",
	})
}

func main() {
	http.HandleFunc("/quantum-compiler/compile", compileHandler)
	http.HandleFunc("/quantum-compiler/health", healthHandler)
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"service": "HyperCode Quantum Esoteric Compiler",
			"version": "1.0.0",
			"endpoints": []string{
				"/quantum-compiler/compile - Compile Brainfuck to Qiskit",
				"/quantum-compiler/health  - Health check",
			},
			"usage": "POST /quantum-compiler/compile with JSON body: {\"code\": \"++++[>++<-]\"}",
		})
	})

	port := ":8081"
	fmt.Printf("🚀 Quantum Compiler starting on http://localhost%s\n", port)
	fmt.Printf("📡 Endpoints:\n")
	fmt.Printf("   - POST/GET /quantum-compiler/compile?code=<brainfuck>\n")
	fmt.Printf("   - GET /quantum-compiler/health\n")
	fmt.Printf("\n🧪 Test: curl \"http://localhost%s/quantum-compiler/compile?code=++++[>++<-]\"\n", port)
	
	if err := http.ListenAndServe(port, nil); err != nil {
		fmt.Printf("Error starting server: %v\n", err)
	}
}
