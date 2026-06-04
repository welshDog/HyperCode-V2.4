"""
Multi-Agent Code Review Crew
3 agents: Coder, QA, Security
Fast local inference with Mistral
"""

import requests
import json
from dataclasses import dataclass
import time
import sys
import io

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral:latest"

@dataclass
class CodeReview:
    file_path: str
    code: str
    coder_review: str = ""
    qa_review: str = ""
    security_review: str = ""
    verdict: str = ""

def query_mistral(prompt: str) -> str:
    """Get response from Mistral"""
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "temperature": 0.5,
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        if response.status_code == 200:
            return response.json().get("response", "No response")
        else:
            return f"Error: {response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"

def review_code_quality(code: str) -> str:
    """Agent 1: Code Quality Review"""
    prompt = f"""Review this code for quality:
1. Clarity and readability
2. Function complexity
3. Variable naming
4. Documentation
5. Design patterns

CODE:
```
{code[:2000]}
```

Give concise feedback."""
    return query_mistral(prompt)

def review_qa(code: str) -> str:
    """Agent 2: QA & Testability"""
    prompt = f"""Review for QA:
1. Is it testable?
2. Edge cases?
3. Error handling?
4. Input validation?
5. Code coverage?

CODE:
```
{code[:2000]}
```

List test scenarios."""
    return query_mistral(prompt)

def review_security(code: str) -> str:
    """Agent 3: Security"""
    prompt = f"""Security review:
1. Injection risks?
2. Auth issues?
3. Data exposure?
4. Vulnerable deps?
5. OWASP issues?

CODE:
```
{code[:2000]}
```

Rate: SAFE / LOW / MEDIUM / HIGH / CRITICAL"""
    return query_mistral(prompt)

def run_crew(file_path: str) -> CodeReview:
    """Run all 3 agents"""
    try:
        with open(file_path, "r") as f:
            code = f.read()
    except FileNotFoundError:
        print(f"ERROR: File not found: {file_path}")
        return None
    
    print("\n" + "="*80)
    print(f"CODE REVIEW CREW - {file_path}")
    print("="*80 + "\n")
    
    review = CodeReview(file_path=file_path, code=code)
    
    # Agent 1: Coder
    print("[1/3] CODER Agent - Code Quality...")
    start = time.time()
    review.coder_review = review_code_quality(code)
    elapsed = time.time() - start
    print(f"Done ({elapsed:.1f}s)\n")
    print(review.coder_review)
    print("\n" + "-"*80 + "\n")
    
    # Agent 2: QA
    print("[2/3] QA Agent - Testability...")
    start = time.time()
    review.qa_review = review_qa(code)
    elapsed = time.time() - start
    print(f"Done ({elapsed:.1f}s)\n")
    print(review.qa_review)
    print("\n" + "-"*80 + "\n")
    
    # Agent 3: Security
    print("[3/3] SECURITY Agent - Vulnerabilities...")
    start = time.time()
    review.security_review = review_security(code)
    elapsed = time.time() - start
    print(f"Done ({elapsed:.1f}s)\n")
    print(review.security_review)
    print("\n" + "-"*80 + "\n")
    
    print("[CREW] Final Verdict")
    print("="*80)
    print(f"Status: REVIEW COMPLETE")
    print(f"File: {file_path}")
    print(f"Lines: {len(code.split(chr(10)))}")
    
    return review

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python multi_agent_crew.py <file>")
        sys.exit(1)
    
    run_crew(sys.argv[1])
