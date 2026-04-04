#!/bin/bash
# FFE Server Cleanup Script
# Cleans Docker build cache, old images, unused volumes, and old data files.
# Safe to run periodically via cron.
#
# Usage: ./ffe_cleanup.sh [--dry-run]

set -euo pipefail

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# ---------------------------------------------------------------------------
# 1. Docker build cache (biggest offender — can be 100GB+)
# ---------------------------------------------------------------------------
log "=== Docker Build Cache ==="
CACHE_SIZE=$(docker system df --format '{{.Size}}' | tail -1)
log "Current build cache: $CACHE_SIZE"

if $DRY_RUN; then
    log "[DRY RUN] Would prune Docker build cache (keep last 7 days)"
else
    log "Pruning build cache older than 7 days..."
    docker builder prune --filter "until=168h" -f 2>/dev/null || true
fi

# ---------------------------------------------------------------------------
# 2. Dangling / unused Docker images
# ---------------------------------------------------------------------------
log "=== Docker Images ==="
DANGLING=$(docker images -f "dangling=true" -q | wc -l)
log "Dangling images: $DANGLING"

# Old tagged images (not the current backend or postgres)
OLD_IMAGES=$(docker images --format '{{.ID}} {{.Repository}}:{{.Tag}} {{.CreatedSince}}' \
    | grep -v "finance_feedback_engine-backend:latest" \
    | grep -v "postgres:16-alpine" \
    | grep -v "<none>" \
    | grep -E "weeks|months" \
    | awk '{print $1}')

if $DRY_RUN; then
    log "[DRY RUN] Would remove $DANGLING dangling images"
    [ -n "$OLD_IMAGES" ] && log "[DRY RUN] Would remove old tagged images: $(echo $OLD_IMAGES | wc -w)"
else
    if [ "$DANGLING" -gt 0 ]; then
        log "Removing dangling images..."
        docker image prune -f 2>/dev/null || true
    fi
    if [ -n "$OLD_IMAGES" ]; then
        log "Removing old tagged images..."
        echo "$OLD_IMAGES" | xargs -r docker rmi -f 2>/dev/null || true
    fi
fi

# ---------------------------------------------------------------------------
# 3. Unused Docker volumes
# ---------------------------------------------------------------------------
log "=== Docker Volumes ==="
# Only prune volumes not attached to running containers
UNUSED_VOLS=$(docker volume ls -f "dangling=true" -q | wc -l)
log "Dangling volumes: $UNUSED_VOLS"

if $DRY_RUN; then
    log "[DRY RUN] Would prune $UNUSED_VOLS dangling volumes"
else
    if [ "$UNUSED_VOLS" -gt 0 ]; then
        log "Pruning dangling volumes..."
        docker volume prune -f 2>/dev/null || true
    fi
fi

# ---------------------------------------------------------------------------
# 4. Old FFE decision files (keep last 14 days)
# ---------------------------------------------------------------------------
log "=== FFE Decision Files ==="
DECISIONS_DIR="/home/cmp6510/finance_feedback_engine/data/decisions"
if [ -d "$DECISIONS_DIR" ]; then
    OLD_DECISIONS=$(find "$DECISIONS_DIR" -name "*.json" -mtime +14 | wc -l)
    OLD_BAKS=$(find "$DECISIONS_DIR" -name "*.bak" | wc -l)
    log "Decision files older than 14 days: $OLD_DECISIONS"
    log "Backup (.bak) files: $OLD_BAKS"

    if $DRY_RUN; then
        log "[DRY RUN] Would remove $OLD_DECISIONS old decisions + $OLD_BAKS .bak files"
    else
        if [ "$OLD_DECISIONS" -gt 0 ]; then
            log "Removing old decision files..."
            find "$DECISIONS_DIR" -name "*.json" -mtime +14 -delete
        fi
        if [ "$OLD_BAKS" -gt 0 ]; then
            log "Removing .bak files..."
            find "$DECISIONS_DIR" -name "*.bak" -delete
        fi
    fi
else
    log "Decisions dir not found on host, checking container..."
    OLD_IN_CONTAINER=$(docker exec ffe-backend find /app/data/decisions -name "*.json" -mtime +14 2>/dev/null | wc -l)
    OLD_BAKS_CONTAINER=$(docker exec ffe-backend find /app/data/decisions -name "*.bak" 2>/dev/null | wc -l)
    log "Old decisions in container: $OLD_IN_CONTAINER, bak files: $OLD_BAKS_CONTAINER"
    if ! $DRY_RUN && [ "$OLD_IN_CONTAINER" -gt 0 ]; then
        docker exec ffe-backend find /app/data/decisions -name "*.json" -mtime +14 -delete 2>/dev/null || true
    fi
    if ! $DRY_RUN && [ "$OLD_BAKS_CONTAINER" -gt 0 ]; then
        docker exec ffe-backend find /app/data/decisions -name "*.bak" -delete 2>/dev/null || true
    fi
fi

# ---------------------------------------------------------------------------
# 5. Old crash dumps, exports, temp files
# ---------------------------------------------------------------------------
log "=== Misc Cleanup ==="
for subdir in crash_dumps exports dlq training_logs; do
    TARGET="/home/cmp6510/finance_feedback_engine/data/$subdir"
    if [ -d "$TARGET" ]; then
        SIZE=$(du -sh "$TARGET" 2>/dev/null | awk '{print $1}')
        COUNT=$(find "$TARGET" -type f -mtime +30 | wc -l)
        log "$subdir: $SIZE total, $COUNT files older than 30 days"
        if ! $DRY_RUN && [ "$COUNT" -gt 0 ]; then
            find "$TARGET" -type f -mtime +30 -delete
        fi
    fi
done

# ---------------------------------------------------------------------------
# 6. Old worktree builds
# ---------------------------------------------------------------------------
log "=== Old Worktree/Scratch Dirs ==="
for d in /home/cmp6510/finance_feedback_engine_cov_* /home/cmp6510/finance_feedback_engine_scratch_* /home/cmp6510/finance_feedback_engine_observability_*; do
    if [ -d "$d" ]; then
        SIZE=$(du -sh "$d" 2>/dev/null | awk '{print $1}')
        log "Old dir: $d ($SIZE)"
        if ! $DRY_RUN; then
            log "Removing $d..."
            rm -rf "$d"
        fi
    fi
done

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
log "=== Post-Cleanup Disk Usage ==="
df -h / | awk 'NR==2 {print "Disk: " $3 " / " $2 " (" $5 ")"}'
docker system df 2>/dev/null | head -5

log "Done."
