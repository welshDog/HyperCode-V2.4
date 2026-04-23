#!/bin/bash
# ============================================================================
# HyperCode Docker Compose Backup Strategy
# ============================================================================
# Purpose: Backup critical volumes (HC_DATA_ROOT) to preserve infrastructure state
# Volumes backed up:
#  - PostgreSQL (postgres-data) — database state
#  - Grafana (grafana-data) — dashboards + config
#  - Prometheus (prometheus-data) — metrics history
#  - Ollama (ollama-data) — LLM models
#  - Agent Memory (agent_memory) — long-term agent state
#  - ChromaDB (chroma_data) — vector embeddings
#  - Tempo (tempo-data) — distributed traces
#  - Loki (loki-data) — log aggregates
#  - Alertmanager (alertmanager-data) — alert config
#
# Schedule: Run daily via cron (e.g., `0 2 * * * /path/to/backup.sh`)
# Retention: Keep last 7 days of backups locally, push to offsite weekly

set -e

# ============================================================================
# CONFIG
# ============================================================================
HC_DATA_ROOT="${HC_DATA_ROOT:-./.hypercode-data}"
BACKUP_DIR="${BACKUP_DIR:-./.hypercode-backups}"
RETENTION_DAYS=${RETENTION_DAYS:-7}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="hypercode-backup-${TIMESTAMP}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"
LOG_FILE="${BACKUP_DIR}/backup.log"

# ============================================================================
# FUNCTIONS
# ============================================================================

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

error_exit() {
    log "ERROR: $*"
    exit 1
}

backup_volume() {
    local volume_name=$1
    local dest_path="${BACKUP_PATH}/${volume_name}"
    log "Backing up volume: $volume_name → $dest_path"
    mkdir -p "$dest_path"
    cp -r "${HC_DATA_ROOT}/${volume_name}" "$dest_path" 2>/dev/null || {
        log "WARNING: Could not backup ${volume_name} (may not exist yet)"
    }
}

cleanup_old_backups() {
    log "Cleaning up backups older than $RETENTION_DAYS days..."
    find "$BACKUP_DIR" -maxdepth 1 -name "hypercode-backup-*" -type d -mtime +$RETENTION_DAYS -exec rm -rf {} + 2>/dev/null || true
}

check_requirements() {
    for cmd in docker tar; do
        command -v "$cmd" >/dev/null 2>&1 || error_exit "Required command not found: $cmd"
    done
}

# ============================================================================
# MAIN
# ============================================================================

check_requirements

log "========== BACKUP START =========="
log "Backup destination: $BACKUP_PATH"

# Create backup directory
mkdir -p "$BACKUP_DIR"
mkdir -p "$BACKUP_PATH"

# Stop potentially running containers that may have open file handles
log "Pausing critical services to ensure consistency..."
docker compose pause postgres 2>/dev/null || true
sleep 2

# Backup each volume
log "Backing up volumes..."
backup_volume "postgres"
backup_volume "grafana"
backup_volume "prometheus"
backup_volume "ollama"
backup_volume "agent_memory"
backup_volume "chroma"
backup_volume "tempo"
backup_volume "loki"
backup_volume "alertmanager"

# Resume paused containers
log "Resuming services..."
docker compose unpause postgres 2>/dev/null || true

# Create tar archive for offsite storage
log "Creating compressed archive..."
tar -czf "${BACKUP_PATH}.tar.gz" -C "$BACKUP_DIR" "$BACKUP_NAME" 2>/dev/null || {
    log "WARNING: Could not create tar.gz (disk space?)"
}

# Cleanup old backups
cleanup_old_backups

log "Backup size: $(du -sh "$BACKUP_PATH" | cut -f1)"
if [ -f "${BACKUP_PATH}.tar.gz" ]; then
    log "Archive size: $(du -sh "${BACKUP_PATH}.tar.gz" | cut -f1)"
fi

log "========== BACKUP COMPLETE =========="
log "To restore, extract backup and run: docker compose restart"
