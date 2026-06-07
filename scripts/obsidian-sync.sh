#!/bin/sh
# ============================================================================
# Obsidian vault sync — results -> PARA session note -> GitHub push.
#
# Two modes (single source of truth):
#   one-shot (default)  : setup, sync once, exit.  (used by `docker compose run`)
#   watch (WATCH_MODE=true): setup once, then watch $RESULTS_DIR and sync on
#                            change.  No docker CLI / socket needed — the crew
#                            orchestrator just writes files; this reacts.
# ============================================================================
set -u

# ── Config ──────────────────────────────────────────────────────────────────
WORKSPACE_DIR="${WORKSPACE_DIR:-/workspace/sync-env}"
RESULTS_DIR="${RESULTS_DIR:-/results}"
HANDOVER_DIR="${HANDOVER_DIR:-/handovers}"
VAULT_REPO="${VAULT_REPO:-git@github.com:welshDog/BROski-Obsidian-Brain-for-HyperFocus-z0ne.git}"
DEFAULT_BRANCH="${DEFAULT_BRANCH:-main}"
DRY_RUN="${DRY_RUN:-false}"
WATCH_MODE="${WATCH_MODE:-false}"
WATCH_INTERVAL="${WATCH_INTERVAL:-15}"
SESSION_NOTE_PREFIX="${SESSION_NOTE_PREFIX:-HYPERAGENT_LOOP}"
SKILL_FILE_BASENAME="${SKILL_FILE_BASENAME:-HYPERAGENTLOOPSYNC}"
SKILL_VERSION="${SKILL_VERSION:-1}"

# ── One-time setup ──────────────────────────────────────────────────────────
setup_deps() {
  # alpine has neither git nor ssh by default
  apk add --no-cache git openssh-client 2>/dev/null || apk add --no-cache git openssh-client
}

setup_ssh() {
  echo "[obsidian-sync] Setting up SSH auth..."
  mkdir -p /root/.ssh
  chmod 700 /root/.ssh
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
}

# ── Change detection ────────────────────────────────────────────────────────
results_fingerprint() {
  cat "${RESULTS_DIR}/latest-summary.md" \
      "${RESULTS_DIR}/latest-metrics.json" \
      "${RESULTS_DIR}/latest-report.md" 2>/dev/null | md5sum | awk '{print $1}'
}

# ── The sync itself (clone -> build note -> commit -> push). Returns 0/1. ────
do_sync() {
  DATE_UTC="$(date -u +%Y-%m-%d)"
  STAMP_UTC="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
  echo "[obsidian-sync] Sync run @ ${STAMP_UTC} (DRY_RUN=${DRY_RUN})"
  echo "[obsidian-sync] Vault repo: $VAULT_REPO"

  mkdir -p "$WORKSPACE_DIR" "$RESULTS_DIR" "$HANDOVER_DIR"
  cd "$WORKSPACE_DIR" || return 1

  # Fresh clone every run — stateless
  rm -rf "$WORKSPACE_DIR/vault" 2>/dev/null || true
  if ! git clone "$VAULT_REPO" vault; then
    echo "[ERROR] Failed to clone vault repo: $VAULT_REPO"
    return 1
  fi
  echo "[obsidian-sync] Vault cloned"
  cd "$WORKSPACE_DIR/vault" || return 1

  git config user.name "${GIT_AUTHOR_NAME:-BROski Bot}"
  git config user.email "${GIT_AUTHOR_EMAIL:-broski-bot@hyperfocus.zone}"
  git fetch origin "$DEFAULT_BRANCH" || return 1
  git checkout "$DEFAULT_BRANCH" || return 1
  echo "[obsidian-sync] Checked out $DEFAULT_BRANCH"

  # Load HyperAgent output (create placeholders if missing)
  RUN_SUMMARY_FILE="${RESULTS_DIR}/latest-summary.md"
  RUN_METRICS_FILE="${RESULTS_DIR}/latest-metrics.json"
  RUN_REPORT_FILE="${RESULTS_DIR}/latest-report.md"
  [ -f "$RUN_SUMMARY_FILE" ] || printf '# HyperAgent Loop Summary\n**Status:** Placeholder (no results yet)\n' > "$RUN_SUMMARY_FILE"
  [ -f "$RUN_METRICS_FILE" ] || printf '{"status": "placeholder", "message": "Waiting for HyperAgent loop output"}\n' > "$RUN_METRICS_FILE"
  [ -f "$RUN_REPORT_FILE" ] || printf '# HyperAgent Review\n**Status:** Awaiting HyperAgent loop completion.\n' > "$RUN_REPORT_FILE"

  # PARA-correct vault paths
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
    return 0
  fi
  git commit -m "feat: sync HyperAgent loop — ${STAMP_UTC}" || return 1

  if [ "$DRY_RUN" = "true" ]; then
    echo "[obsidian-sync] DRY_RUN=true — skipping push"
  else
    echo "[obsidian-sync] Pushing to origin/$DEFAULT_BRANCH..."
    git push origin "$DEFAULT_BRANCH" || return 1
    echo "[obsidian-sync] ✅ Pushed $(git rev-parse --short HEAD)"
  fi
  echo "[obsidian-sync] Nice one BROski♾️! Vault sync complete — $(basename "$SESSION_NOTE")"
  return 0
}

# ── Main ────────────────────────────────────────────────────────────────────
echo "[obsidian-sync] Boot — WATCH_MODE=${WATCH_MODE} DRY_RUN=${DRY_RUN}"
setup_deps
setup_ssh

if [ "$WATCH_MODE" != "true" ]; then
  # One-shot
  do_sync
  exit $?
fi

# Watch mode: only act on changes that appear AFTER we start (avoids a spurious
# push on every container restart). Debounce so we don't read a half-written set.
echo "[obsidian-watch] Watching ${RESULTS_DIR} every ${WATCH_INTERVAL}s (debounced)"
LAST_FP="$(results_fingerprint)"
echo "[obsidian-watch] Initial baseline fingerprint: ${LAST_FP:-<none>}"
while true; do
  sleep "$WATCH_INTERVAL"
  FP="$(results_fingerprint)"
  [ -z "$FP" ] && continue
  [ "$FP" = "$LAST_FP" ] && continue

  # Debounce: confirm the fingerprint is stable before syncing
  sleep 3
  FP2="$(results_fingerprint)"
  if [ "$FP2" != "$FP" ]; then
    echo "[obsidian-watch] Results still changing — deferring"
    continue
  fi

  echo "[obsidian-watch] Change detected (${LAST_FP} -> ${FP}) — syncing…"
  if do_sync; then
    LAST_FP="$FP"
    echo "[obsidian-watch] Sync OK — new baseline ${LAST_FP}"
  else
    echo "[obsidian-watch] Sync FAILED — will retry next interval (baseline unchanged)"
  fi
done
