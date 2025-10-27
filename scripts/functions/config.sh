#!/bin/bash

create_config_xml() {
    log_info "Creating configuration file..."
    
    cat > "$CONFIG_FILE" <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<kurslight>
  <version>1.0.0</version>
  <installation_date>$(date -Iseconds)</installation_date>
  
  <radius_config>
    <enabled>false</enabled>
    <server>radius.example.com</server>
    <port>1812</port>
    <secret>radius_secret</secret>
    <timeout>5</timeout>
    <retries>3</retries>
  </radius_config>
  
  <syslog_config>
    <enabled>true</enabled>
    <server>localhost</server>
    <port>514</port>
    <protocol>udp</protocol>
    <facility>local0</facility>
    <level>info</level>
  </syslog_config>
  
  <vpn_instances>
    <instance>
      <name>default</name>
      <description>Default VPN Server</description>
      <role>server</role>
      <protocol>udp</protocol>
      <port>1194</port>
      <dev_type>tun</dev_type>
      <subnet>10.8.0.0 255.255.255.0</subnet>
      <topology>subnet</topology>
      <encryption>AES-256-CBC</encryption>
      <status>stopped</status>
      <local_network></local_network>
      <push_routes></push_routes>
      <push_dns>8.8.8.8,1.1.1.1</push_dns>
      <push_ntp></push_ntp>
      <redirect_gateway>1</redirect_gateway>
      <client_to_client>0</client_to_client>
      <duplicate_cn>0</duplicate_cn>
      <block_ipv6>1</block_ipv6>
      <float>0</float>
      <passtos>0</passtos>
      <persist_remote_ip>0</persist_remote_ip>
      <remote_random>0</remote_random>
      <tls_auth>0</tls_auth>
      <verify_client_cert>1</verify_client_cert>
      <certificate_depth>1</certificate_depth>
      <renegotiate_time>3600</renegotiate_time>
      <auth_token_lifetime>0</auth_token_lifetime>
      <additional_config></additional_config>
    </instance>
  </vpn_instances>
  
  <certificates>
    <certificate type="server">
      <name>server</name>
      <created>$(date -Iseconds)</created>
      <status>active</status>
    </certificate>
    <certificate type="client">
      <name>client1</name>
      <created>$(date -Iseconds)</created>
      <status>active</status>
    </certificate>
  </certificates>
  
  <external_certificates/>
  
  <database>
    <host>localhost</host>
    <port>5432</port>
    <name>kurslight_db</name>
    <user>kurslight_user</user>
  </database>
  
</kurslight>
XML

    chmod 600 "$CONFIG_FILE"
    log_success "Configuration file created: $CONFIG_FILE"
}

setup_syslog() {
    log_info "Setting up Syslog configuration..."
    
    cat > "/etc/rsyslog.d/$APP_NAME.conf" <<'SYSLOG'
# KursLight VPN Management System logs
if $programname == 'kurs-light' then {
    action(type="omfile" file="/opt/kurs-light/logs/kurslight.log")
    stop
}

# OpenVPN logs through syslog
if $programname == 'openvpn' then {
    action(type="omfile" file="/opt/kurs-light/logs/openvpn.log")
    stop
}

# Application specific logs
if $syslogtag contains 'kurs-light' then {
    action(type="omfile" file="/opt/kurs-light/logs/application.log")
    stop
}
SYSLOG

    # Create log files with proper permissions
    touch "$LOG_DIR/kurslight.log"
    touch "$LOG_DIR/openvpn.log" 
    touch "$LOG_DIR/application.log"
    
    chmod 644 "$LOG_DIR"/*.log
    systemctl restart rsyslog
    
    log_success "Syslog configuration completed"
}