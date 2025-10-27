#!/bin/bash

set -e

echo "🔍 Starting comprehensive installation verification..."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
        ((PASSED++))
    else
        echo -e "${RED}❌ $2${NC}"
        ((FAILED++))
    fi
}

# Check services
echo "Checking services..."
services=("postgresql" "nginx" "kurs-light")
for service in "${services[@]}"; do
    systemctl is-active --quiet "$service"
    print_result $? "Service $service is running"
done

# Check ports
echo "Checking ports..."
ports=("80" "443" "5000" "1194")
for port in "${ports[@]}"; do
    netstat -tuln | grep ":$port " > /dev/null
    print_result $? "Port $port is listening"
done

# Check directories
echo "Checking directories..."
directories=("/opt/kurs-light" "/opt/kurs-light/backend" "/opt/kurs-light/ca" "/opt/kurs-light/logs")
for dir in "${directories[@]}"; do
    [ -d "$dir" ]
    print_result $? "Directory $dir exists"
done

# Test web interface
echo "Testing web interface..."
curl -k -s https://localhost > /dev/null
print_result $? "Web interface is accessible"

# Test database connectivity
echo "Testing database connectivity..."
psql -U kurslight_user -d kurslight_db -c "SELECT 1;" > /dev/null 2>&1
print_result $? "Database connectivity OK"

# Test API endpoints
echo "Testing API endpoints..."
API_BASE="https://localhost:5000/api"

# Test authentication
curl -k -s -X POST "$API_BASE/auth/login" -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}' > /dev/null
print_result $? "API authentication endpoint"

# Test health endpoint
curl -k -s "$API_BASE/health" > /dev/null
print_result $? "API health endpoint"

# Summary
echo
echo "📊 Verification Summary:"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All checks passed! Installation is successful.${NC}"
    exit 0
else
    echo -e "${RED}💥 Some checks failed. Please review the installation.${NC}"
    exit 1
fi