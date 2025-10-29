#!/bin/bash

setup_openvpn_ca() {
    log_info "Setting up OpenVPN Certificate Authority..."
    
    cleanup_existing_ca
    copy_easy_rsa
    initialize_ca
    generate_dh_params
    generate_server_certificate
    generate_client_certificate
    secure_ca_files
    
    log_success "OpenVPN CA setup completed"
}

cleanup_existing_ca() {
    rm -rf "$CA_DIR"
    mkdir -p "$CA_DIR"
}

copy_easy_rsa() {
    log_info "Copying EasyRSA..."
    
    local easyrsa_src="/usr/share/easy-rsa"
    if [ ! -d "$easyrsa_src" ]; then
        log_error "EasyRSA not found. Please install easy-rsa package."
        exit 1
    fi
    
    cp -r "$easyrsa_src"/* "$CA_DIR"/
}

initialize_ca() {
    log_info "Initializing Certificate Authority..."
    
    cd "$CA_DIR"
    
    if [ -f "./easyrsa" ]; then
        log_info "Using EasyRSA v2..."
        initialize_ca_v2
    elif [ -f "./3/easyrsa" ]; then
        log_info "Using EasyRSA v3..."
        initialize_ca_v3
    else
        log_error "EasyRSA executable not found"
        exit 1
    fi
}

initialize_ca_v2() {
    chmod +x ./easyrsa
    export EASYRSA_BATCH=1
    ./easyrsa init-pki
    echo | ./easyrsa build-ca nopass
}

initialize_ca_v3() {
    cd ./3
    chmod +x ./easyrsa
    export EASYRSA_BATCH=1
    ./easyrsa init-pki
    echo "KursLight-CA" | ./easyrsa build-ca nopass
    cd ..
}

generate_dh_params() {
    log_info "Generating DH parameters (this may take a while)..."
    
    cd "$CA_DIR"
    
    if [ -f "./easyrsa" ]; then
        ./easyrsa gen-dh
    elif [ -f "./3/easyrsa" ]; then
        cd ./3
        ./easyrsa gen-dh
        cd ..
    fi
}

generate_server_certificate() {
    log_info "Generating server certificate..."
    
    cd "$CA_DIR"
    
    if [ -f "./easyrsa" ]; then
        echo | ./easyrsa build-server-full server nopass
    elif [ -f "./3/easyrsa" ]; then
        cd ./3
        echo | ./easyrsa build-server-full server nopass
        cd ..
    fi
}

generate_client_certificate() {
    log_info "Generating client certificate..."
    
    cd "$CA_DIR"
    
    if [ -f "./easyrsa" ]; then
        echo | ./easyrsa build-client-full client1 nopass
    elif [ -f "./3/easyrsa" ]; then
        cd ./3
        echo | ./easyrsa build-client-full client1 nopass
        cd ..
    fi
}

secure_ca_files() {
    log_info "Securing CA files..."
    
    chmod 600 "$CA_DIR"/pki/private/* 2>/dev/null || true
    chmod 644 "$CA_DIR"/pki/issued/* 2>/dev/null || true
    chmod 644 "$CA_DIR"/pki/ca.crt 2>/dev/null || true
    chmod 644 "$CA_DIR"/pki/dh.pem 2>/dev/null || true
}