#!/bin/bash
# ...existing code...
# colors must be defined in helpers.sh before sourcing this file

# Ensure LOG_DIR is set by the caller (install.sh)
: "${LOG_DIR:=/var/log/kurs-light}"

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
    mkdir -p "$LOG_DIR"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] $1" >> "$LOG_DIR/install.log"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    mkdir -p "$LOG_DIR"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [SUCCESS] $1" >> "$LOG_DIR/install.log"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    mkdir -p "$LOG_DIR"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [WARNING] $1" >> "$LOG_DIR/install.log"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    mkdir -p "$LOG_DIR"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $1" >> "$LOG_DIR/install.log"
}

setup_logging() {
    mkdir -p "$LOG_DIR"
    # tee to logfile while preserving colors in terminal
    exec > >(tee -a "$LOG_DIR/install.log") 2>&1
}
# ...existing code...