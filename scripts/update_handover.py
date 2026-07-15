import subprocess
from datetime import datetime

date = datetime.now().strftime("%Y-%m-%d")
filename = f"NEXT_SESSION_HANDOVER_{date}.md"

content = f"""# Next Session Handover — {date}

## Last Agent Task
Auto-captured by Hook on task completion.

## Status
- [ ] Review changes
- [ ] Push commits
- [ ] Update WHATS_DONE.md
"""

with open(filename, "w") as f:
    f.write(content)

subprocess.run(["git", "add", filename])
subprocess.run(["git", "commit", "-m", f"chore: auto-handover {date}"])
subprocess.run(["git", "push"])
print(f"✅ Handover created and pushed: {filename}")
