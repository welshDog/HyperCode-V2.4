#!/bin/bash

# Docker Backup Script for HyperCode
# Backs up volumes, configs, and database

set -e

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
COMPOSE_FILE="${1:-docker-compose.yml}"

echo "💾 HyperCode Docker Backup Utility"
echo "==================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Create backup directory
mkdir -p "$BACKUP_DIR/$TIMESTAMP"

# Backup PostgreSQL
backup_postgres() {
    echo "Backing up PostgreSQL database..."
    
    local container=$(docker-compose -f "$COMPOSE_FILE" ps -q postgres)
    if [ -z "$container" ]; then
        echo "PostgreSQL container not found"
        return 1
    fi
    
    docker exec "$container" pg_dump -U postgres hypercode | gzip > "$BACKUP_DIR/$TIMESTAMP/postgres-hypercode.sql.gz"
    
    echo -e "${GREEN}✓ PostgreSQL backup complete${NC}"
}

# Backup Redis
backup_redis() {
    echo "Backing up Redis..."
    
    local container=$(docker-compose -f "$COMPOSE_FILE" ps -q redis)
    if [ -z "$container" ]; then
        echo "Redis container not found"
        return 1
    fi
    
    # Trigger Redis save
    docker exec "$container" redis-cli SAVE
    
    # Copy dump file
    docker cp "$container:/data/dump.rdb" "$BACKUP_DIR/$TIMESTAMP/redis-dump.rdb"
    
    echo -e "${GREEN}✓ Redis backup complete${NC}"
}

# Backup Docker volumes
backup_volumes() {
    echo "Backing up Docker volumes..."

    # Enumerate volumes from compose config to avoid silent "no volumes backed up"
    # when volume names don't match a simple grep pattern.
    local volumes
    volumes=$(docker compose -f "$COMPOSE_FILE" config --volumes 2>/dev/null || true)

    if [ -z "$volumes" ]; then
        echo "${YELLOW}⚠ No volumes found via compose config; falling back to docker volume ls${NC}"
        # Compose prefixes volumes with the project name; use that prefix
        local project
        project=$(docker compose -f "$COMPOSE_FILE" config --format json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('name',''))" 2>/dev/null || true)
        if [ -n "$project" ]; then
            volumes=$(docker volume ls --format "{{.Name}}" | grep "^${project}_" || true)
        fi
    fi

    if [ -z "$volumes" ]; then
        echo "No volumes found to back up"
        return
    fi

    for volume in $volumes; do
        # Resolve the fully-qualified volume name if compose returned a short name
        local fq_volume="$volume"
        if ! docker volume inspect "$volume" > /dev/null 2>&1; then
            local project
            project=$(docker compose -f "$COMPOSE_FILE" config --format json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('name',''))" 2>/dev/null || true)
            fq_volume="${project}_${volume}"
        fi

        if docker volume inspect "$fq_volume" > /dev/null 2>&1; then
            echo "  Backing up volume: $fq_volume"
            docker run --rm \
                -v "$fq_volume:/data:ro" \
                -v "$PWD/$BACKUP_DIR/$TIMESTAMP:/backup" \
                alpine tar czf "/backup/${fq_volume}.tar.gz" -C /data .
        else
            echo "${YELLOW}  ⚠ Volume '$fq_volume' not found, skipping${NC}"
        fi
    done

    echo -e "${GREEN}✓ Volume backups complete${NC}"
}

# Backup configurations
backup_configs() {
    echo "Backing up configurations..."

    # Copy compose files (safe — no secrets)
    cp docker-compose*.yml "$BACKUP_DIR/$TIMESTAMP/" 2>/dev/null || true
    cp -r Configuration_Kit "$BACKUP_DIR/$TIMESTAMP/" 2>/dev/null || true
    cp -r monitoring "$BACKUP_DIR/$TIMESTAMP/" 2>/dev/null || true

    # SECURITY: .env files contain live credentials — never copy them into backups.
    # Rotate secrets before restoring to a new environment; use .env.example as the template.
    echo "${YELLOW}  ⚠ Skipping .env files — they contain live secrets. Use .env.example as the restore template.${NC}"

    echo -e "${GREEN}✓ Configuration backup complete${NC}"
}

# Create manifest
create_manifest() {
    echo "Creating backup manifest..."
    
    cat > "$BACKUP_DIR/$TIMESTAMP/MANIFEST.txt" <<EOF
HyperCode Backup Manifest
========================
Date: $(date)
Compose File: $COMPOSE_FILE
Docker Version: $(docker --version)

Contents:
- PostgreSQL database dump
- Redis dump
- Docker volumes
- Configuration files

Containers backed up:
$(docker-compose -f "$COMPOSE_FILE" ps --services)

To restore:
  1. Extract volumes: docker run --rm -v volume_name:/data -v \$(pwd):/backup alpine tar xzf /backup/volume.tar.gz -C /data
  2. Restore PostgreSQL: gunzip -c postgres-hypercode.sql.gz | docker exec -i postgres psql -U postgres hypercode
  3. Restore Redis: docker cp redis-dump.rdb container:/data/dump.rdb && docker exec container redis-cli SHUTDOWN SAVE
EOF
    
    echo -e "${GREEN}✓ Manifest created${NC}"
}

# Compress entire backup
compress_backup() {
    echo "Compressing backup..."
    
    cd "$BACKUP_DIR"
    tar czf "hypercode-backup-$TIMESTAMP.tar.gz" "$TIMESTAMP"
    rm -rf "$TIMESTAMP"
    
    echo -e "${GREEN}✓ Backup compressed: hypercode-backup-$TIMESTAMP.tar.gz${NC}"
}

# Cleanup old backups (keep last 7 days)
cleanup_old_backups() {
    echo "Cleaning up old backups..."
    
    find "$BACKUP_DIR" -name "hypercode-backup-*.tar.gz" -mtime +7 -delete
    
    echo -e "${GREEN}✓ Old backups cleaned${NC}"
}

# Main
main() {
    echo "Starting backup to: $BACKUP_DIR/$TIMESTAMP"
    echo ""
    
    backup_postgres
    backup_redis
    backup_volumes
    backup_configs
    create_manifest
    compress_backup
    cleanup_old_backups
    
    echo ""
    echo "==================================="
    echo -e "${GREEN}✅ Backup complete!${NC}"
    echo ""
    echo "Backup location: $BACKUP_DIR/hypercode-backup-$TIMESTAMP.tar.gz"
    echo ""
    echo "To restore:"
    echo "  1. Extract: tar xzf hypercode-backup-$TIMESTAMP.tar.gz"
    echo "  2. Run: ./scripts/docker-restore.sh $TIMESTAMP"
}

main "$@"
