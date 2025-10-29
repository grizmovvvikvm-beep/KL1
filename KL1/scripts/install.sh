#!/bin/bash
set -e

# ================= CONFIGURATION =================
APP_NAME="kurs-light"
APP_DIR="/opt/$APP_NAME"
LOG_DIR="$APP_DIR/logs"

# ================= SOURCE FILES =================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/logging.sh"
source "$SCRIPT_DIR/utils/helpers.sh"
source "$SCRIPT_DIR/functions/dependencies.sh"
source "$SCRIPT_DIR/functions/database.sh"
source "$SCRIPT_DIR/functions/ssl.sh"
source "$SCRIPT_DIR/functions/openvpn.sh"
source "$SCRIPT_DIR/functions/backend.sh"
source "$SCRIPT_DIR/functions/frontend.sh"
source "$SCRIPT_DIR/functions/system.sh"

# ================= MAIN INSTALLATION =================
main() {
    log_info "🚀 Starting KursLight VPN Management System installation"
    
    # Check root privileges
    check_root
    
    # Create directory structure
    create_directories
    
    # Installation steps
    install_dependencies
    setup_postgresql
    setup_ssl
    setup_openvpn_ca
    create_config_xml
    setup_syslog
    create_backend
    create_frontend
    setup_nginx
    configure_firewall
    setup_selinux
    start_services
    
    display_final_info
    log_success "✅ Installation completed successfully"
}

# Run main function
main "$@"