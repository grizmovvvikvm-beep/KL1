#!/bin/bash
# OpenVPN RADIUS Authentication Script
# Called by OpenVPN for user authentication

LOG_TAG="openvpn-radius-auth"
RADIUS_SERVER="127.0.0.1"
RADIUS_SECRET="radius_secret"
RADIUS_PORT="1812"

log_message() {
    logger -t "$LOG_TAG" "$1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> /opt/kurs-light/logs/openvpn/radius-auth.log
}

# Parse command line arguments
USERNAME="$1"
PASSWORD="$2"
REMOTE_IP="$3"
PORT="$4"
PROTO="$5"

# Validate input
if [ -z "$USERNAME" ] || [ -z "$PASSWORD" ]; then
    log_message "ERROR: Missing username or password"
    exit 1
fi

# RADIUS authentication using radclient
AUTH_REQUEST="User-Name=$USERNAME,User-Password=$PASSWORD,NAS-IP-Address=127.0.0.1,NAS-Port=$PORT,NAS-Identifier=kurs-light-vpn,Service-Type=Framed-User,Framed-Protocol=PPP"

# Send RADIUS request
RESPONSE=$(echo "$AUTH_REQUEST" | radclient -r 1 -t 3 $RADIUS_SERVER:$RADIUS_PORT auth $RADIUS_SECRET 2>/dev/null)

# Check response
if echo "$RESPONSE" | grep -q "Access-Accept"; then
    log_message "SUCCESS: User $USERNAME authenticated from $REMOTE_IP"
    
    # Extract RADIUS attributes
    FRAMED_IP=$(echo "$RESPONSE" | grep "Framed-IP-Address" | cut -d= -f2 | tr -d ' ')
    if [ -n "$FRAMED_IP" ]; then
        echo "ifconfig-push $FRAMED_IP 255.255.255.0"
    fi
    
    # Push routes if specified
    FRAMED_ROUTE=$(echo "$RESPONSE" | grep "Framed-Route" | cut -d= -f2 | tr -d ' ')
    if [ -n "$FRAMED_ROUTE" ]; then
        echo "push \"route $FRAMED_ROUTE\""
    fi
    
    exit 0
else
    log_message "FAILED: Authentication failed for user $USERNAME from $REMOTE_IP"
    exit 1
fi