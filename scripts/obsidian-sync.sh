#!/bin/sh
set -eu

# ── Install deps (alpine has neither git nor ssh by default) ────────────
apk add --no-cache git openssh-client 2>/dev/null

# ── Environment variables ──────────────────────────────────────────
DATE_UTC="$(date -u +%Y-%m-%d)"
STAMP_UTC="$(date -u +%Y-%m-%dT%H-%M-%SZ)"

WORKSPACE_DIR="${WORKSPACE_DIR:-/workspace/sync-env}"
RESULTS_DIR="${RESULTS_DIR:-/results}"
HANDOVER_DIR="${HANDOVER_DIR:-/handovers}"
VAULT_REPO="${VAULT_REPO:-git@github.com:welshDog/BROski-Obsidian-Brain-for-HyperFocus-z0ne.git}"
DEFAULT_BRANCH="${DEFAULT_BRANCH:-main}"
DRY_RUN="${DRY_RUN:-false}"

SESSION_NOTE_PREFIX="${SESSION_NOTE_PREFIX:-HYPERAGENT_LOOP}"
SKILL_FILE_BASENAME="${SKILL_FILE_BASENAME:-HYPERAGENTLOOPSYNC}"
SKILL_VERSION="${SKILL_VERSION:-1}"

echo "[obsidian-sync] Starting stateless vault sync"
echo "[obsidian-sync] Workspace: $WORKSPACE_DIR"
echo "[obsidian-sync] Vault repo: $VAULT_REPO"
echo "[obsidian-sync] DRY_RUN: $DRY_RUN"

# ── Setup directories ──────────────────────────────────────────────
mkdir -p "$WORKSPACE_DIR" "$RESULTS_DIR" "$HANDOVER_DIR"
cd "$WORKSPACE_DIR"

# ── SSH auth ────────────────────────────────────────────────────────────────
echo "[obsidian-sync] Setting up SSH auth..."
mkdir -p /root/.ssh
chmod 700 /root/.ssh

# Copy SSH keys from read-only host mount (/root/.ssh-host) to writable /root/.ssh
if [ -f /root/.ssh-host/id_ed25519 ]; then
  cp /root/.ssh-host/id_ed25519 /root/.ssh/id_ed25519
  chmod 600 /root/.ssh/id_ed25519
  echo "[obsidian-sync] SSH key copied from /root/.ssh-host"
else
  echo "[ERROR] No SSH key found at /root/.ssh-host/id_ed25519"
  echo "[ERROR] Mount your SSH key: ~/.ssh:/root/.ssh-host:ro"
  exit 1
fi

# Trust GitHub host key — no interactive prompt
ssh-keyscan -H github.com >> /root/.ssh/known_hosts 2>/dev/null || true
echo "[obsidian-sync] GitHub host key added to known_hosts"

# ── Clone fresh ────────────────────────────────────────────────────────────────
echo "[obsidian-sync] Cloning vault repository..."
rm -rf "$WORKSPACE_DIR/vault" 2>/dev/null || true

if ! git clone "$VAULT_REPO" vault; then
  echo "[ERROR] Failed to clone vault repo: $VAULT_REPO"
  echo "[ERROR] Check SSH auth and repo URL"
  exit 1
fi

echo "[obsidian-sync] Vault cloned successfully"

cd "$WORKSPACE_DIR/vault"

# ── Configure git ────────────────────────────────────────────────────────────
git config user.name "${GIT_AUTHOR_NAME:-BROski Bot}"
git config user.email "${GIT_AUTHOR_EMAIL:-broski-bot@hyperfocus.zone}"
echo "[obsidian-sync] Git configured"

# ── Fetch latest branch ──────────────────────────────────────────────────────
git fetch origin "$DEFAULT_BRANCH"
git checkout "$DEFAULT_BRANCH"
echo "[obsidian-sync] Checked out $DEFAULT_BRANCH"

# ── Load HyperAgent output ──────────────────────────────────────────────────
echo "[obsidian-sync] Loading HyperAgent results..."

RUN_SUMMARY_FILE="${RESULTS_DIR}/latest-summary.md"
RUN_METRICS_FILE="${RESULTS_DIR}/latest-metrics.json"
RUN_REPORT_FILE="${RESULTS_DIR}/latest-report.md"

[ -f "$RUN_SUMMARY_FILE" ] || { mkdir -p "$RESULTS_DIR"; cat > "$RUN_SUMMARY_FILE" <<'EOF'
# HyperAgent Loop Summary
**Status:** Placeholder (no results yet)
EOF
}

[ -f "$RUN_METRICS_FILE" ] || { mkdir -p "$RESULTS_DIR"; cat > "$RUN_METRICS_FILE" <<'EOF'
{"status": "placeholder", "message": "Waiting for HyperAgent loop output"}
EOF
}

[ -f "$RUN_REPORT_FILE" ] || { mkdir -p "$RESULTS_DIR"; cat > "$RUN_REPORT_FILE" <<'EOF'
# HyperAgent Review
**Status:** Awaiting HyperAgent loop completion.
EOF
}

echo "[obsidian-sync] Results loaded"

# ── PARA-correct vault paths ─────────────────────────────────────────────────
echo "[obsidian-sync] Creating PARA directories..."
SESSION_NOTES_DIR="./HYPERFOCUS_ZONE/05-Focus-Sessions"
SKILL_DIR="./HYPERFOCUS_ZONE/03-Resources/Agent-YAMLs"
INBOX_DIR="./HYPERFOCUS_ZONE/00-Inbox"
mkdir -p "$SESSION_NOTES_DIR" "$SKILL_DIR" "$INBOX_DIR"

SESSION_NOTE="${SESSION_NOTES_DIR}/${SESSION_NOTE_PREFIX}_${STAMP_UTC}.md"
SKILL_FILE="${SKILL_DIR}/${SKILL_FILE_BASENAME}v${SKILL_VERSION}.md"
HANDOVER_FILE="${INBOX_DIR}/NEXTSESSIONHANDOVER_${DATE_UTC}.md"

cat > "$SESSION_NOTE" <<EOF
---
created: ${DATE_UTC}
tags: [hyperagent, sync, focus-session]
status: completed
project: HyperCode-V2.4
priority: high
---

# ${SESSION_NOTE_PREFIX} — ${STAMP_UTC}

## Summary
$(cat "$RUN_SUMMARY_FILE")

## Metrics
\`\`\`json
$(cat "$RUN_METRICS_FILE")
\`\`\`

## Review
$(cat "$RUN_REPORT_FILE")
EOF

[ -f "$SKILL_FILE" ] || cat > "$SKILL_FILE" <<EOF
# ${SKILL_FILE_BASENAME} v${SKILL_VERSION}

## What it Does
Syncs HyperAgent results into Obsidian vault in PARA format.

## Run
\`\`\`bash
docker compose -f docker-compose.obsidian-sync.yml run --rm obsidian-sync
\`\`\`
EOF

cat > "$HANDOVER_FILE" <<EOF
# NEXT SESSION HANDOVER — ${DATE_UTC}

## Completed
- Vault note: \`$(basename "$SESSION_NOTE")\`
- Skill file: \`$(basename "$SKILL_FILE")\`
- Branch: \`${DEFAULT_BRANCH}\`
- Synced: \`${STAMP_UTC}\`

## Next Tasks
1. Review session note in \`05-Focus-Sessions/\`
2. Promote winner or iterate
3. Update WHATSDONE.md if permanent
EOF

git add "$SESSION_NOTE" "$SKILL_FILE" "$HANDOVER_FILE"

if git diff --cached --quiet; then
  echo "[obsidian-sync] No changes to commit"
  exit 0
fi

git commit -m "feat: sync HyperAgent loop — ${STAMP_UTC}"

if [ "$DRY_RUN" = "true" ]; then
  echo "[obsidian-sync] DRY_RUN=true — skipping push"
else
  echo "[obsidian-sync] Pushing to origin/$DEFAULT_BRANCH..."
  git push origin "$DEFAULT_BRANCH"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Nice one BROski♾️! Vault sync complete."
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Session note: $SESSION_NOTE"
echo "Skill file:   $SKILL_FILE"
echo "Handover:     $HANDOVER_FILE"
echo "Commit:       $(git rev-parse --short HEAD)"
[ "$DRY_RUN" = "true" ] && echo "(DRY_RUN — no push)" || echo "✅ Pushed to GitHub"
echo ""
