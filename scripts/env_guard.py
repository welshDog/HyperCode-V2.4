import subprocess
import sys

DANGEROUS_PATTERNS = [
    ".env",
    ".env.local",
    ".env.production",
    ".env.staging",
]

SECRET_KEYWORDS = [
    "SECRET",
    "PASSWORD",
    "TOKEN",
    "API_KEY",
    "PRIVATE_KEY",
    "STRIPE_",
    "SUPABASE_",
    "DISCORD_TOKEN",
    "GITHUB_PAT",
]

def get_staged_files():
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True, text=True
    )
    return result.stdout.strip().splitlines()

def check_staged_content():
    result = subprocess.run(
        ["git", "diff", "--cached"],
        capture_output=True, text=True
    )
    return result.stdout

staged = get_staged_files()
blocked = False

# Check 1 — .env files staged directly
for f in staged:
    for pattern in DANGEROUS_PATTERNS:
        if f == pattern or f.endswith("/" + pattern):
            print(f"\n🚨 SACRED RULE VIOLATION 🚨")
            print(f"❌ BLOCKED: '{f}' is a .env file — NEVER commit secrets!")
            print(f"💡 Run: git reset HEAD {f}")
            blocked = True

# Check 2 — secret keywords in staged content
if not blocked:
    content = check_staged_content()
    for keyword in SECRET_KEYWORDS:
        if f"+{keyword}=" in content or f"+ {keyword}=" in content:
            print(f"\n🚨 SACRED RULE VIOLATION 🚨")
            print(f"❌ BLOCKED: Looks like '{keyword}' value is staged in a commit!")
            print(f"💡 Check your staged files: git diff --cached")
            blocked = True
            break

if blocked:
    print("\n🔒 Hook blocked this action. Fix the issue first.")
    sys.exit(1)
else:
    print("✅ .env guard passed — no secrets detected.")
