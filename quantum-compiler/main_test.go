package main

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func TestCompileBFEmitsPlainPythonOnly(t *testing.T) {
	out := compileBF("++>.<,[]")

	for _, forbidden := range []string{"```", "<html", "</", "<?xml", "<xml", "<!--"} {
		if strings.Contains(strings.ToLower(out), forbidden) {
			t.Fatalf("output contains forbidden artifact: %q", forbidden)
		}
	}

	required := []string{
		"from __future__ import annotations",
		"import math",
		"from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister",
		"def build_circuit(source: str) -> QuantumCircuit:",
		"qc.rx(math.pi / 8, qr[0])",
		"qc.swap(qr[0], qr[1])",
		"qc.h(qr[0])",
		"qc.measure(qr, cr)",
	}
	for _, want := range required {
		if !strings.Contains(out, want) {
			t.Fatalf("output missing required snippet: %q", want)
		}
	}
}

func TestGeneratedPythonIsSyntaxValid(t *testing.T) {
	out := compileBF("++++[>++<-]")
	tmp := t.TempDir()
	path := filepath.Join(tmp, "compiled.py")
	if err := os.WriteFile(path, []byte(out), 0o600); err != nil {
		t.Fatalf("write temp file: %v", err)
	}

	cmd := exec.Command("python", "-m", "py_compile", path)
	combined, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("py_compile failed: %v\n%s", err, string(combined))
	}
}

func TestGeneratedCircuitRunsIfQiskitInstalled(t *testing.T) {
	check := exec.Command("python", "-c", "import qiskit; import qiskit.quantum_info")
	if err := check.Run(); err != nil {
		t.Skip("qiskit not installed; skipping runtime import/simulation check")
	}

	out := compileBF("++>+<-")
	tmp := t.TempDir()
	path := filepath.Join(tmp, "compiled.py")
	if err := os.WriteFile(path, []byte(out), 0o600); err != nil {
		t.Fatalf("write temp file: %v", err)
	}

	cmd := exec.Command("python", path)
	combined, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("running generated code failed: %v\n%s", err, string(combined))
	}
}

