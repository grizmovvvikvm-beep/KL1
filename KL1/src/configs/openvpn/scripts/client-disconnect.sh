#!/bin/bash
# OpenVPN Client Disconnect Script
# Called when client disconnects

LOG_TAG="openvpn-client-disconnect"
USERNAME="$1"
SESSION_ID="$2"
REMOTE_IP="$3"
VIRTUAL_IP="$4"
BYTES_SENT="$5"
BYTES_RECEIVED="$6"
DURATION="$7"

log_message() {
    logger -t "$LOG_TAG" "$1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> /opt/kurs-light/logs/openvpn/client-connections.log
}

# Calculate session time in seconds
SESSION_TIME=$(echo "$DURATION" | awk -F: '{ print ($1 * 3600) + ($2 * 60) + $3 }')

# Log disconnection
log_message "DISCONNECT: User $USERNAME from $REMOTE_IP (Duration: $DURATION, Sent: $BYTES_SENT, Received: $BYTES_RECEIVED)"

# Update database
psql -d kurslight_db -c "
UPDATE vpn_connection_logs 
SET 
    action = 'disconnect',
    bytes_sent = $BYTES_SENT,
    bytes_received = $BYTES_RECEIVED,
    duration_seconds = $SESSION_TIME,
    disconnected_at = NOW()
WHERE session_id = '$SESSION_ID';" 2>/dev/null || true

# Send RADIUS accounting stop
ACCT_REQUEST="User-Name=$USERNAME,Acct-Session-Id=$SESSION_ID,NAS-IP-Address=127.0.0.1,Acct-Status-Type=Stop,Acct-Session-Time=$SESSION_TIME,Acct-Input-Octets=$BYTES_RECEIVED,Acct-Output-Octets=$BYTES_SENT,Framed-IP-Address=$VIRTUAL_IP"

echo "$ACCT_REQUEST" | radclient -r 1 -t 2 127.0.0.1:1813 acct radius_secret >/dev/null 2>&1 &

exit 0