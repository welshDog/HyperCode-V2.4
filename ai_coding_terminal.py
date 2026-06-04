#!/usr/bin/env python3
"""
AI Coding Terminal - Real-time Mistral inference
Neurodivergent-optimized for HyperFocus Z0ne
"""

import requests
import json
import sys
import time

# Force UTF-8
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral:latest"

def stream_response(prompt: str):
    """Stream Mistral response token-by-token"""
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": True,
        "temperature": 0.7,
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, stream=True, timeout=120)
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                if "response" in data:
                    yield data["response"]
                if data.get("done"):
                    break
    except Exception as e:
        yield f"\nERROR: {str(e)}\n"

def ask(query: str):
    """Ask Mistral anything"""
    print(f"\n>>> Your question: {query}\n")
    print("[Mistral thinking...]\n")
    print("-" * 80)
    
    start_time = time.time()
    token_count = 0
    
    for chunk in stream_response(query):
        print(chunk, end="", flush=True)
        token_count += len(chunk.split())
    
    elapsed = time.time() - start_time
    print("\n" + "-" * 80)
    print(f"\nStats: {token_count} tokens | {elapsed:.1f}s | {token_count/max(elapsed, 0.1):.0f} tok/s\n")

def code_review(file_path: str):
    """Review code with Mistral"""
    try:
        with open(file_path, "r") as f:
            code = f.read()
    except FileNotFoundError:
        print(f"ERROR: File not found: {file_path}")
        return
    
    prompt = f"""Review this code for:
1. Bugs or logic errors
2. Performance issues  
3. Security problems
4. Best practices

CODE:
```
{code}
```

Provide actionable feedback, prioritized by severity."""
    
    print(f"\n[Code Review: {file_path}]\n")
    print("-" * 80)
    
    for chunk in stream_response(prompt):
        print(chunk, end="", flush=True)
    
    print("\n" + "-" * 80 + "\n")

def hyperfocus_mode(task: str, minutes: int = 25):
    """Enter hyperfocus mode with AI guidance"""
    prompt = f"""I'm entering hyperfocus mode for {minutes} minutes.
Guide me through this task step-by-step. SHORT, CLEAR instructions.
Each step should take ~5 minutes max.

TASK: {task}

Format each step like:
Step 1: [do this]
Step 2: [then this]

Make it FAST and ACTIONABLE. No fluff."""
    
    print(f"\n[HYPERFOCUS MODE - {minutes} minutes]")
    print(f"Task: {task}\n")
    print("=" * 80)
    
    for chunk in stream_response(prompt):
        print(chunk, end="", flush=True)
    
    print("\n" + "=" * 80)
    print(f"\nSet a {minutes}-minute timer and GO!\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python ai_coding_terminal.py ask '<question>'")
        print("  python ai_coding_terminal.py review <file>")
        print("  python ai_coding_terminal.py hyperfocus '<task>' [minutes]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "ask":
        query = sys.argv[2] if len(sys.argv) > 2 else input("Your question: ")
        ask(query)
    elif command == "review":
        file_path = sys.argv[2] if len(sys.argv) > 2 else input("File to review: ")
        code_review(file_path)
    elif command == "hyperfocus":
        task = sys.argv[2] if len(sys.argv) > 2 else input("Task: ")
        minutes = int(sys.argv[3]) if len(sys.argv) > 3 else 25
        hyperfocus_mode(task, minutes)
    else:
        print(f"Unknown command: {command}")
