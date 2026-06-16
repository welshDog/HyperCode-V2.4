import subprocess
from datetime import datetime
import os

WHATS_DONE = "WHATS_DONE.md"
date = datetime.now().strftime("%Y-%m-%d")
time_str = datetime.now().strftime("%H:%M")

def get_todays_commits():
    """Grab today's commit messages to auto-populate WHATS_DONE."""
    result = subprocess.run(
        ["git", "log", "--oneline", "--since=midnight"],
        capture_output=True, text=True
    )
    lines = result.stdout.strip().splitlines()
    return lines if lines else ["No commits today"]

def get_changed_files():
    """Get files changed in this session."""
    result = subprocess.run(
        ["git", "diff", "HEAD~1", "--name-only"],
        capture_output=True, text=True
    )
    return result.stdout.strip().splitlines()

print(f"\n\ud83c� Session ending — {date} {time_str}")
print("\ud83d� Auto-updating WHATS_DONE.md...")

commits = get_todays_commits()
files = get_changed_files()

# Build new entry
entry_lines = [
    f"\n---\n",
    f"## Session — {date} {time_str}\n",
    f"### ✅ Commits Today\n",
]
for c in commits:
    entry_lines.append(f"- {c}\n")

if files:
    entry_lines.append(f"\n### 📂 Files Changed\n")
    for f in files[:20]:  # cap at 20 so it doesn't go huge
        entry_lines.append(f"- `{f}`\n")

entry_lines.append(f"\n### 💡 Notes\n")
entry_lines.append(f"_Auto-captured by TRAE SessionEnd hook at {time_str}_\n")

new_entry = "".join(entry_lines)

# Append to WHATS_DONE.md
if os.path.exists(WHATS_DONE):
    with open(WHATS_DONE, "a") as f:
        f.write(new_entry)
    print(f"✅ WHATS_DONE.md updated with today's session")
else:
    with open(WHATS_DONE, "w") as f:
        f.write(f"# WHATS_DONE\n")
        f.write(new_entry)
    print(f"✅ WHATS_DONE.md created fresh")

# Commit and push
subprocess.run(["git", "add", WHATS_DONE])
result = subprocess.run(
    ["git", "commit", "-m", f"chore: auto-session-log {date} {time_str}"],
    capture_output=True, text=True
)

if "nothing to commit" in result.stdout:
    print("💬 No new changes to log")
else:
    subprocess.run(["git", "push"])
    print(f"🚀 WHATS_DONE.md committed and pushed!")

print(f"\n🦙 BROski Z0ne closed. See you next session Bro! 🤙")
