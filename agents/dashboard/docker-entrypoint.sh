#!/bin/sh
set -eu

STATIC_DIR="/app/.next/static"
CHUNKS_DIR="/app/.next/static/chunks"
BACKUP_DIR="/app/.next_static_backup"

if [ ! -d "$CHUNKS_DIR" ]; then
  if [ -d "$BACKUP_DIR" ]; then
    rm -rf "$STATIC_DIR" || true
    mkdir -p "/app/.next"
    cp -R "$BACKUP_DIR" "$STATIC_DIR"
  fi
fi

exec node server.js

