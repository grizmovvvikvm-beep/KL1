#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

# Check distribution
get_distribution() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo $ID
    else
        log_error "Cannot determine distribution"
        exit 1
    fi
}

# Create directory structure
create_directories() {
    log_info "Creating directory structure..."
    
    local dirs=(
        "$APP_DIR"
        "$APP_DIR/backend"
        "$APP_DIR/frontend" 
        "$APP_DIR/logs"
        "$APP_DIR/openvpn/servers"
        "$APP_DIR/ca"
        "$APP_DIR/ssl"
        "$APP_DIR/certs/external"
        "$APP_DIR/backups"
        "$APP_DIR/templates"
        "$APP_DIR/static"
    )
    
    for dir in "${dirs[@]}"; do
        mkdir -p "$dir"
    done
    
    chmod 755 "$APP_DIR"
    chmod 750 "$LOG_DIR"
}

# Generate random password
generate_password() {
    local length=${1:-32}
    openssl rand -base64 "$length" 2>/dev/null || echo "default_password_$(date +%s)"
}

# Wait for service
wait_for_service() {
    local service_name=$1
    local max_attempts=${2:-10}
    local wait_seconds=${3:-2}
    
    log_info "Waiting for $service_name to start..."
    
    for ((i=1; i<=max_attempts; i++)); do
        if systemctl is-active --quiet "$service_name"; then
            log_success "$service_name is running"
            return 0
        fi
        log_info "Attempt $i/$max_attempts - waiting ${wait_seconds}s..."
        sleep "$wait_seconds"
    done
    
    log_error "$service_name failed to start"
    return 1
}