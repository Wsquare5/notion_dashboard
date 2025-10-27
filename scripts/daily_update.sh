#!/bin/bash
# Daily Binance data update script
# Updates perp-only trading data to Notion

set -e  # Exit on error

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Log file with timestamp
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/daily_update_$(date +%Y%m%d_%H%M%S).log"

# Function to log with timestamp
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=========================================="
log "Starting daily Binance data update"
log "=========================================="

cd "$PROJECT_ROOT"

# Step 1: Regenerate perp-only list
log "Step 1: Regenerating perp-only token list..."
if python3 scripts/filter_perp_only.py >> "$LOG_FILE" 2>&1; then
    log "✅ Perp-only list updated"
else
    log "❌ Failed to update perp-only list"
    exit 1
fi

# Step 2: Update Binance trading data for perp-only tokens
log ""
log "Step 2: Updating Binance trading data (perp-only)..."
if python3 scripts/update_binance_trading_data.py --perp-only >> "$LOG_FILE" 2>&1; then
    log "✅ Binance trading data updated"
else
    log "⚠️  Some errors occurred during Binance data update (check log)"
fi

# Optional Step 3: Recalculate MC/FDV (if needed)
log ""
log "Step 3: Recalculating MC/FDV..."
if python3 scripts/recalculate_mc_fdv.py >> "$LOG_FILE" 2>&1; then
    log "✅ MC/FDV recalculation complete"
else
    log "⚠️  Some errors occurred during MC/FDV recalculation (check log)"
fi

log ""
log "=========================================="
log "Daily update complete!"
log "Log saved to: $LOG_FILE"
log "=========================================="

# Keep only last 30 days of logs
find "$LOG_DIR" -name "daily_update_*.log" -mtime +30 -delete

exit 0
