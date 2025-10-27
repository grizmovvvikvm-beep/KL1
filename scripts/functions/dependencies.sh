#!/bin/bash

install_dependencies() {
    log_info "Installing system dependencies..."
    
    local distribution=$(get_distribution)
    
    case $distribution in
        "centos"|"rhel"|"fedora")
            install_dependencies_redhat
            ;;
        "debian"|"ubuntu")
            install_dependencies_debian
            ;;
        *)
            log_error "Unsupported distribution: $distribution"
            exit 1
            ;;
    esac
    
    install_python_dependencies
    log_success "Dependencies installed successfully"
}

install_dependencies_redhat() {
    log_info "Installing packages for RedHat-based systems..."
    
    if command -v dnf &> /dev/null; then
        dnf update -y
        dnf install -y epel-release
        dnf groupinstall -y "Development Tools"
        dnf install -y \
            python3 python3-virtualenv python3-pip python3-devel \
            openvpn easy-rsa xmlstarlet unzip curl nginx openssl wget \
            postgresql postgresql-server postgresql-contrib \
            openssl-devel openvpn-devel libpq-devel postgresql-devel \
            policycoreutils-python-utils setroubleshoot rsyslog \
            net-tools iproute firewalld
    elif command -v yum &> /dev/null; then
        yum update -y
        yum install -y epel-release
        yum groupinstall -y "Development Tools"
        yum install -y \
            python3 python3-virtualenv python3-pip python3-devel \
            openvpn easy-rsa xmlstarlet unzip curl nginx openssl wget \
            postgresql postgresql-server postgresql-contrib \
            openssl-devel openvpn-devel libpq-devel postgresql-devel \
            policycoreutils-python-utils setroubleshoot rsyslog \
            net-tools iproute firewalld
    else
        log_error "Neither dnf nor yum found"
        exit 1
    fi
}

install_dependencies_debian() {
    log_info "Installing packages for Debian-based systems..."
    
    apt-get update
    apt-get install -y \
        python3 python3-venv python3-pip python3-dev \
        openvpn easy-rsa xmlstarlet unzip curl nginx openssl wget \
        postgresql postgresql-contrib \
        libssl-dev libopenvpn-dev libpq-dev postgresql-server-dev-all \
        policycoreutils setools rsyslog \
        net-tools iproute2 ufw
}

install_python_dependencies() {
    log_info "Installing Python pip if missing..."
    
    if ! command -v pip3 &> /dev/null; then
        curl -s https://bootstrap.pypa.io/get-pip.py -o get-pip.py
        python3 get-pip.py
        rm get-pip.py
    fi
}