#!/usr/bin/env sh
set -eu

# Make sure runtime paths expected by the app are backed by persistent storage.
# main.py and other modules write to ./output and ./chroma_db, so we symlink them.
OUTPUT_DIR="${OUTPUT_DIR:-/var/data/output}"
CHROMA_PERSIST_DIR="${CHROMA_PERSIST_DIR:-/var/data/chroma_db}"
DB_PATH="${DB_PATH:-${OUTPUT_DIR}/governance_data.db}"

export OUTPUT_DIR CHROMA_PERSIST_DIR DB_PATH

mkdir -p "$OUTPUT_DIR" "$CHROMA_PERSIST_DIR"

# Create stable paths inside /app used by the codebase.
# Only create symlinks if the target paths don't already exist.
# This keeps `docker-compose` bind mounts / named volumes working.
if [ ! -e /app/output ]; then
  ln -s "$OUTPUT_DIR" /app/output
fi

if [ ! -e /app/chroma_db ]; then
  ln -s "$CHROMA_PERSIST_DIR" /app/chroma_db
fi

exec "$@"

