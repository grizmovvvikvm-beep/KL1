#!/bin/bash

setup_ssl() {
    log_info "Setting up SSL certificates..."
    
    mkdir -p "$SSL_DIR"
    
    if [ ! -f "$SSL_CERT" ] || [ ! -f "$SSL_KEY" ]; then
        generate_ssl_certificates
    else
        log_info "Using existing SSL certificates"
    fi
    
    secure_ssl_files
    log_success "SSL setup completed"
}

generate_ssl_certificates() {
    log_info "Generating self-signed SSL certificates..."
    
    local hostname=$(hostname)
    local subject="/C=RU/ST=Moscow/L=Moscow/O=KursLight/OU=IT/CN=$hostname"
    
    openssl req -x509 -nodes -days 825 -newkey rsa:2048 \
        -keyout "$SSL_KEY" -out "$SSL_CERT" \
        -subj "$subject" 2>/dev/null
    
    log_success "SSL certificates generated: $SSL_CERT, $SSL_KEY"
}

secure_ssl_files() {
    chmod 600 "$SSL_KEY" 2>/dev/null || true
    chmod 644 "$SSL_CERT" 2>/dev/null || true
    chown root:root "$SSL_KEY" "$SSL_CERT" 2>/dev/null || true
}