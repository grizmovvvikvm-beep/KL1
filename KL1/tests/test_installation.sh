#!/bin/bash

echo "Running installation tests..."

# Test functions
test_directory_structure() {
    echo "Testing directory structure..."
    local app_dir="/opt/kurs-light"
    
    local dirs=(
        "$app_dir"
        "$app_dir/backend"
        "$app_dir/frontend"
        "$app_dir/logs"
        "$app_dir/openvpn/servers"
        "$app_dir/ca"
        "$app_dir/ssl"
    )
    
    for dir in "${dirs[@]}"; do
        if [ -d "$dir" ]; then
            echo "✓ Directory exists: $dir"
        else
            echo "✗ Directory missing: $dir"
            return 1
        fi
    done
}

test_services_running() {
    echo "Testing services..."
    
    local services=(
        "postgresql"
        "nginx"
        "kurs-light"
    )
    
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service"; then
            echo "✓ Service running: $service"
        else
            echo "✗ Service not running: $service"
            return 1
        fi
    done
}

test_web_interface() {
    echo "Testing web interface..."
    
    local url="https://localhost"
    if curl -k -s --head "$url" | grep "200 OK" > /dev/null; then
        echo "✓ Web interface accessible"
    else
        echo "✗ Web interface not accessible"
        return 1
    fi
}

# Run tests
test_directory_structure
test_services_running
test_web_interface

echo "Installation tests completed!"