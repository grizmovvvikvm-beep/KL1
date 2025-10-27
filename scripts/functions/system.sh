#!/bin/bash

setup_nginx() {
    log_info "Setting up Nginx..."
    
    create_nginx_config
    test_nginx_config
    start_nginx_service
    
    log_success "Nginx setup completed"
}

create_nginx_config() {
    cat > "/etc/nginx/conf.d/$APP_NAME.conf" <<NGINX
server {
    listen 80;
    server_name _;
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name _;
    
    ssl_certificate $SSL_CERT;
    ssl_certificate_key $SSL_KEY;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    location / {
        proxy_pass https://127.0.0.1:$WEB_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
        send_timeout 300;
    }
    
    location /static/ {
        alias $APP_DIR/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
NGINX
}

test_nginx_config() {
    if ! nginx -t; then
        log_error "Nginx configuration test failed"
        exit 1
    fi
}

start_nginx_service() {
    systemctl enable nginx
    systemctl start nginx
    wait_for_service "nginx" 5 2
}

configure_firewall() {
    log_info "Configuring firewall..."
    
    if command -v firewall-cmd &> /dev/null; then
        firewall-cmd --permanent --add-service=http
        firewall-cmd --permanent --add-service=https
        firewall-cmd --permanent --add-service=openvpn
        firewall-cmd --permanent --add-port=1194/udp
        firewall-cmd --permanent --add-port=1194/tcp
        firewall-cmd --reload
        log_success "Firewall configured"
    else
        log_warning "firewalld not available, skipping firewall configuration"
    fi
}

setup_selinux() {
    log_info "Configuring SELinux..."
    
    if command -v semanage &> /dev/null; then
        setsebool -P httpd_can_network_connect 1
        setsebool -P openvpn_can_network_connect 1
        semanage fcontext -a -t httpd_sys_content_t "$APP_DIR(/.*)?"
        restorecon -R "$APP_DIR"
        log_success "SELinux configured"
    else
        log_warning "SELinux tools not available, skipping SELinux configuration"
    fi
}

start_services() {
    log_info "Starting application services..."
    
    systemctl daemon-reload
    systemctl enable "$APP_NAME"
    systemctl start "$APP_NAME"
    
    if wait_for_service "$APP_NAME" 10 3; then
        log_success "Application service started successfully"
    else
        log_error "Application service failed to start"
        log_info "Check logs with: journalctl -u $APP_NAME -n 50 --no-pager"
        exit 1
    fi
}

display_final_info() {
    local ip_address=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")
    
    echo ""
    echo "=================================================="
    echo "🎉 INSTALLATION COMPLETED SUCCESSFULLY!"
    echo "=================================================="
    echo ""
    echo "🌐 ACCESS INFORMATION:"
    echo "   • Web Interface: https://$ip_address"
    echo "   • Direct Access: https://$ip_address:$WEB_PORT"
    echo ""
    echo "🔐 DEFAULT CREDENTIALS:"
    echo "   • Username: admin"
    echo "   • Password: admin123"
    echo "   ⚠️  Change password after first login!"
    echo ""
    echo "📁 DIRECTORIES:"
    echo "   • Application: $APP_DIR"
    echo "   • Logs: $LOG_DIR"
    echo "   • Configs: $APP_DIR/config.xml"
    echo ""
    echo "🛠️ MANAGEMENT COMMANDS:"
    echo "   • Service status: systemctl status $APP_NAME"
    echo "   • Stop service: systemctl stop $APP_NAME"
    echo "   • Start service: systemctl start $APP_NAME"
    echo "   • View logs: journalctl -u $APP_NAME -f"
    echo ""
    echo "📚 NEXT STEPS:"
    echo "   1. Access the web interface"
    echo "   2. Change admin password"
    echo "   3. Configure VPN servers"
    echo "   4. Generate client configurations"
    echo ""
    echo "=================================================="
    echo ""
}