#!/bin/bash

set -e

echo "🔄 Starting KursLight VPN Update..."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

APP_DIR="/opt/kurs-light"
BACKUP_DIR="$APP_DIR/backups"
UPDATE_LOG="$APP_DIR/logs/update.log"

# Logging
exec > >(tee -a "$UPDATE_LOG")
exec 2>&1

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

error() {
    echo -e "${RED}$1${NC}"
    log "ERROR: $1"
}

success() {
    echo -e "${GREEN}$1${NC}"
    log "SUCCESS: $1"
}

info() {
    echo -e "${YELLOW}$1${NC}"
    log "INFO: $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    error "Please run as root"
    exit 1
fi

# Backup current installation
info "📦 Creating backup..."
cd "$APP_DIR"
python3 scripts/utils/backup.py

# Stop services
info "⏹️ Stopping services..."
systemctl stop kurs-light

# Update code
info "📥 Updating application..."
cd "$APP_DIR"

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    error "Not a git repository. Cannot update."
    exit 1
fi

# Fetch latest changes
git fetch origin

# Check if there are updates
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u})

if [ "$LOCAL" = "$REMOTE" ]; then
    info "🎉 Already up-to-date."
    exit 0
fi

info "📝 Found updates. Applying..."
git merge origin/master

# Update dependencies
info "📚 Updating dependencies..."
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/backend/requirements.txt"

# Run database migrations
info "🗄️ Updating database..."
if [ -f "$APP_DIR/backend/migrate.py" ]; then
    "$APP_DIR/venv/bin/python" "$APP_DIR/backend/migrate.py"
else
    info "No migration script found. Skipping."
fi

# Restart services
info "🔄 Restarting services..."
systemctl start kurs-light

# Wait for services to start
sleep 5

# Verify installation
info "🔍 Verifying installation..."
if "$APP_DIR/tests/verify_installation.sh"; then
    success "✅ Update completed successfully!"
else
    error "💥 Update verification failed. Rolling back..."
    
    # TODO: Implement rollback from backup
    error "Rollback not yet implemented. Please check system status."
    exit 1
fi