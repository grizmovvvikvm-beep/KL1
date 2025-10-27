#!/bin/bash
# OpenVPN Client Connect Script
# Called when client connects

LOG_TAG="openvpn-client-connect"
USERNAME="$1"
SESSION_ID="$2"
REMOTE_IP="$3"
VIRTUAL_IP="$4"

log_message() {
    logger -t "$LOG_TAG" "$1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> /opt/kurs-light/logs/openvpn/client-connections.log
}

# Log connection
log_message "CONNECT: User $USERNAME connected from $REMOTE_IP (VIP: $VIRTUAL_IP, Session: $SESSION_ID)"

# Update database
psql -d kurslight_db -c "
INSERT INTO vpn_connection_logs 
(username, client_ip, virtual_ip, session_id, action, connected_at) 
VALUES 
('$USERNAME', '$REMOTE_IP', '$VIRTUAL_IP', '$SESSION_ID', 'connect', NOW());" 2>/dev/null || true

# Send RADIUS accounting start
ACCT_REQUEST="User-Name=$USERNAME,Acct-Session-Id=$SESSION_ID,NAS-IP-Address=127.0.0.1,NAS-Port=1194,Acct-Status-Type=Start,Framed-IP-Address=$VIRTUAL_IP"

echo "$ACCT_REQUEST" | radclient -r 1 -t 2 127.0.0.1:1813 acct radius_secret >/dev/null 2>&1 &

exit 0