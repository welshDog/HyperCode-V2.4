import subprocess
import sys

file = sys.argv[1] if len(sys.argv) > 1 else None

if not file or not file.endswith(".py"):
    sys.exit(0)

print(f"\n🔍 Linting: {file}")

with open(file) as f:
    for i, line in enumerate(f, 1):
        if line.startswith("   ") and not line.startswith("    "):
            print(f"❌ Line {i}: 3-space indent detected! Fix to 4 spaces.")
            sys.exit(1)

result = subprocess.run(
    ["ruff", "check", file, "--fix"],
    capture_output=True, text=True
)

if result.returncode != 0:
    print(f"⚠️  Lint issues:\n{result.stdout}")
else:
    print(f"✅ {file} — clean!")

subprocess.run(["black", file, "--quiet"])
print(f"🎨 Black formatted: {file}")
