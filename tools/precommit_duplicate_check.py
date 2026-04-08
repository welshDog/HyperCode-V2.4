import os
import sys
import subprocess

def main():
    if os.getenv("DUP_CHECK_BYPASS", "0").lower() in ("1", "true", "yes"):
        print("[pre-commit] duplicate check bypassed")
        return 0
    maxp = float(os.getenv("DUP_MAX_PERCENT", "5"))
    cmd = [sys.executable, "tools/lean_review.py", "--min-lines", "5", "--top", "5", "--max-dup-percent", str(maxp)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    print(p.stdout)
    if p.returncode != 0:
        print("[pre-commit] duplication exceeds threshold or tests failed")
    return p.returncode

if __name__ == "__main__":
    sys.exit(main())

