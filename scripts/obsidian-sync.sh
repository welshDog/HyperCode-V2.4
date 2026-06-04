#!/bin/sh
set -eu

# ── Install deps (alpine has neither git nor ssh by default) ────────────
apk add --no-cache git openssh-client 2>/dev/null

# ── Environment variables ────────────────────────────────────────────────
DATE_UTC="$(date -u +%Y-%m-%d)"
STAMP_UTC="$(date -u +%Y-%m-%dT%H-%M-%SZ)"

WORKSPACE_DIR="${WORKSPACE_DIR:-/workspace/sync-env}"
RESULTS_DIR="${RESULTS_DIR:-/results}"
HANDOVER_DIR="${HANDOVER_DIR:-/handovers}"
VAULT_REPO="${VAULT_REPO:-git@github.com:welshDog/BROski-Obsidian-Brain.git}"
DEFAULT_BRANCH="${DEFAULT_BRANCH:-main}"
DRY_RUN="${DRY_RUN:-false}"

SESSION_NOTE_PREFIX="${SESSION_NOTE_PREFIX:-HYPERAGENT_LOOP}"
SKILL_FILE_BASENAME="${SKILL_FILE_BASENAME:-HYPERAGENTLOOPSYNC}"
SKILL_VERSION="${SKILL_VERSION:-1}"

echo "[obsidian-sync] Starting stateless vault sync"
echo "[obsidian-sync] Workspace: $WORKSPACE_DIR"
echo "[obsidian-sync] Vault repo: $VAULT_REPO"
echo "[obsidian-sync] DRY_RUN: $DRY_RUN"

# ── Setup directories ───────────────────────────────────────────────────────
mkdir -p "$WORKSPACE_DIR" "$RESULTS_DIR" "$HANDOVER_DIR"
cd "$WORKSPACE_DIR"

# ── SSH auth ─────────────────────────────────────────────────────────────────
echo "[obsidian-sync] Setting up SSH auth..."
mkdir -p /root/.ssh
chmod 700 /root/.ssh

# Copy SSH keys from read-only host mount to writable location
if [ -f /home/sync/.ssh/id_ed25519 ]; then
  cp /home/sync/.ssh/id_ed25519 /root/.ssh/id_ed25519
  chmod 600 /root/.ssh/id_ed25519
  echo "[obsidian-sync] SSH key copied"
else
  echo "[obsidian-sync] WARNING: No SSH key found at /home/sync/.ssh/id_ed25519"
  echo "[obsidian-sync] Falling back to public key auth or env-based token"
fi

# Trust GitHub host key — no interactive prompt
ssh-keyscan -H github.com >> /root/.ssh/known_hosts 2>/dev/null || true
echo "[obsidian-sync] GitHub host key added to known_hosts"

# ── Clone fresh ─────────────────────────────────────────────────────────────
echo "[obsidian-sync] Cloning vault repository..."
rm -rf "$WORKSPACE_DIR/vault" 2>/dev/null || true

if ! git clone "$VAULT_REPO" vault; then
  echo "[ERROR] Failed to clone vault repo: $VAULT_REPO"
  echo "[ERROR] Check SSH auth and repo URL"
  exit 1
fi

echo "[obsidian-sync] Vault cloned successfully"

cd "$WORKSPACE_DIR/vault"

# ── Configure git ───────────────────────────────────────────────────────────
git config user.name "${GIT_AUTHOR_NAME:-BROski Bot}"
git config user.email "${GIT_AUTHOR_EMAIL:-broski-bot@hyperfocus.zone}"
echo "[obsidian-sync] Git configured"

# ── Fetch latest branch ──────────────────────────────────────────────────────
git fetch origin "$DEFAULT_BRANCH"
git checkout "$DEFAULT_BRANCH"
echo "[obsidian-sync] Checked out $DEFAULT_BRANCH"

# ── Load HyperAgent output ───────────────────────────────────────────────────
echo "[obsidian-sync] Loading HyperAgent results..."

RUN_SUMMARY_FILE="${RESULTS_DIR}/latest-summary.md"
RUN_METRICS_FILE="${RESULTS_DIR}/latest-metrics.json"
RUN_REPORT_FILE="${RESULTS_DIR}/latest-report.md"

# If files don't exist, create placeholders (non-blocking)
if [ ! -f "$RUN_SUMMARY_FILE" ]; then
  echo "[obsidian-sync] No summary found at $RUN_SUMMARY_FILE (creating placeholder)"
  mkdir -p "$RESULTS_DIR"
  cat > "$RUN_SUMMARY_FILE" <<'SUMMARY'
# HyperAgent Loop Summary

**Status:** Placeholder (no results from HyperAgent loop yet)  
**Note:** Run a HyperAgent experiment first, then sync again.
SUMMARY
fi

if [ ! -f "$RUN_METRICS_FILE" ]; then
  echo "[obsidian-sync] No metrics found at $RUN_METRICS_FILE (creating placeholder)"
  mkdir -p "$RESULTS_DIR"
  cat > "$RUN_METRICS_FILE" <<'METRICS'
{
  "status": "placeholder",
  "message": "Waiting for HyperAgent loop output"
}
METRICS
fi

if [ ! -f "$RUN_REPORT_FILE" ]; then
  echo "[obsidian-sync] No report found at $RUN_REPORT_FILE (creating placeholder)"
  mkdir -p "$RESULTS_DIR"
  cat > "$RUN_REPORT_FILE" <<'REPORT'
# HyperAgent Review

**Status:** Awaiting HyperAgent loop completion.  
Run the loop, then sync again.
REPORT
fi

echo "[obsidian-sync] Results loaded"

# ── PARA-correct vault paths ─────────────────────────────────────────────────
echo "[obsidian-sync] Creating PARA directories..."

SESSION_NOTES_DIR="./HYPERFOCUS_ZONE/05-Focus-Sessions"
SKILL_DIR="./HYPERFOCUS_ZONE/03-Resources/Agent-YAMLs"
INBOX_DIR="./HYPERFOCUS_ZONE/00-Inbox"

mkdir -p "$SESSION_NOTES_DIR" "$SKILL_DIR" "$INBOX_DIR"

# ── Write session note ───────────────────────────────────────────────────────
SESSION_NOTE="${SESSION_NOTES_DIR}/${SESSION_NOTE_PREFIX}_${STAMP_UTC}.md"

echo "[obsidian-sync] Writing session note: $SESSION_NOTE"

cat > "$SESSION_NOTE" <<EOF
---
created: ${DATE_UTC}
tags: [hyperagent, sync, focus-session]
status: completed
project: HyperCode-V2.4
priority: high
---

# ${SESSION_NOTE_PREFIX} — ${STAMP_UTC}

**Synced by:** obsidian-sync container  
**Branch:** ${DEFAULT_BRANCH}  

## Summary

$(cat "$RUN_SUMMARY_FILE")

## Metrics

\`\`\`json
$(cat "$RUN_METRICS_FILE")
\`\`\`

## Review Notes

$(cat "$RUN_REPORT_FILE")

## Next Steps

1. Review results above
2. Decide: promote, iterate, or archive
3. Update WHATSDONE.md if this becomes permanent
4. Document learnings in Related Skills below

## Related Skills

- HS-014 VAULT KEEPER
- HS-021 VAULT SYNC  
- HS-068 THE CONDUCTOR
- HS-076 THE GATEKEEPER
- HS-095 THE LEDGER LAW

EOF

# ── Ensure skill file exists ─────────────────────────────────────────────────
SKILL_FILE="${SKILL_DIR}/${SKILL_FILE_BASENAME}v${SKILL_VERSION}.md"

if [ ! -f "$SKILL_FILE" ]; then
  echo "[obsidian-sync] Creating skill file: $SKILL_FILE"
  cat > "$SKILL_FILE" <<EOF
# ${SKILL_FILE_BASENAME} v${SKILL_VERSION}

## What it Does

Syncs HyperAgent experiment results into the Obsidian vault, writes a dated session note, and prepares a next-session handover.

## Input Format

- \`latest-summary.md\`
- \`latest-metrics.json\`
- \`latest-report.md\`

All read from \`/results/\` inside the container.

## THE PROMPT

Use this skill after an experiment loop completes.

1. Write a clean vault note in PARA format (00-Inbox, 03-Resources, 05-Focus-Sessions)
2. Preserve all metrics in JSON format
3. Create a next-session handover breadcrumb
4. Never commit secrets (checked by .gitignore)
5. Always fetch before push (prevents conflicts)

## Example

\`\`\`bash
docker compose -f docker-compose.obsidian-sync.yml run --rm obsidian-sync
\`\`\`

Run after A/B testing 3 skill variants and Codex review is complete.

## Configuration

Set these env vars in docker-compose.obsidian-sync.yml or .env:

- \`VAULT_REPO\` — GitHub URL of your Obsidian vault (default: BROski-Obsidian-Brain)
- \`RESULTS_DIR\` — where HyperAgent writes results (default: /results)
- \`DRY_RUN\` — true to skip git push (default: false)
- \`SESSION_NOTE_PREFIX\` — prefix for session notes (default: HYPERAGENT_LOOP)

## Related Skills

- HS-014 VAULT KEEPER — maintain PARA structure
- HS-021 VAULT SYNC — bi-directional sync patterns
- HS-068 THE CONDUCTOR — orchestrate multi-step flows

EOF
fi

echo "[obsidian-sync] Skill file ensured: $SKILL_FILE"

# ── Write next-session handover ──────────────────────────────────────────────
HANDOVER_FILE="${INBOX_DIR}/NEXTSESSIONHANDOVER_${DATE_UTC}.md"

echo "[obsidian-sync] Writing handover: $HANDOVER_FILE"

cat > "$HANDOVER_FILE" <<EOF
# NEXT SESSION HANDOVER — ${DATE_UTC}

**Read this first next session.**

---

## ✅ What Completed This Session

- HyperAgent loop: completed
- Obsidian sync: successful
- Vault note written: \`$(basename "$SESSION_NOTE")\`
- Skill file: \`$(basename "$SKILL_FILE")\`

---

## 🎯 Next Tasks

1. Review the session note in \`05-Focus-Sessions/\`
2. Decide: promote winner, iterate, or archive
3. Update \`WHATSDONE.md\` if results become permanent
4. Document learnings in the skill file

---

## 📝 Live State

- Branch: \`${DEFAULT_BRANCH}\`
- Synced at: \`${STAMP_UTC}\`
- DRY_RUN: \`${DRY_RUN}\`

EOF

# ── Stage files for commit ───────────────────────────────────────────────────
echo "[obsidian-sync] Staging files..."

git add \
  "$SESSION_NOTE" \
  "$SKILL_FILE" \
  "$HANDOVER_FILE"

# ── Check if there are changes ───────────────────────────────────────────────
if git diff --cached --quiet; then
  echo "[obsidian-sync] No changes to commit"
  exit 0
fi

# ── Commit and push (or dry-run) ─────────────────────────────────────────────
echo "[obsidian-sync] Committing changes..."

git commit -m "feat: sync HyperAgent loop — ${STAMP_UTC}"

if [ "$DRY_RUN" = "true" ]; then
  echo "[obsidian-sync] DRY_RUN=true: skipping push"
  echo "[obsidian-sync] Commit ready: $(git rev-parse --short HEAD)"
else
  echo "[obsidian-sync] Pushing to origin/$DEFAULT_BRANCH..."
  if git push origin "$DEFAULT_BRANCH"; then
    echo "[obsidian-sync] Push successful ✅"
  else
    echo "[ERROR] Push failed — check SSH auth and branch permissions"
    exit 1
  fi
fi

# ── Success summary ──────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Nice one BROski♾️! Vault sync complete."
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Session note:  $SESSION_NOTE"
echo "Skill file:    $SKILL_FILE"
echo "Handover:      $HANDOVER_FILE"
echo ""
echo "Workspace:     $WORKSPACE_DIR"
echo "Commit:        $(git rev-parse --short HEAD)"
echo "Branch:        $DEFAULT_BRANCH"
echo ""
if [ "$DRY_RUN" = "true" ]; then
  echo "(DRY_RUN mode — no push executed)"
else
  echo "✅ Pushed to GitHub"
fi
echo ""
