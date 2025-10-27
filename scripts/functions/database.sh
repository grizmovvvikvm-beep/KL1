#!/bin/bash

setup_postgresql() {
    log_info "Setting up PostgreSQL..."
    
    initialize_postgresql
    configure_postgresql
    start_postgresql
    create_database
    log_success "PostgreSQL setup completed"
}

initialize_postgresql() {
    if [ ! -f /var/lib/pgsql/data/postgresql.conf ]; then
        log_info "Initializing PostgreSQL database..."
        postgresql-setup initdb || /usr/bin/initdb /var/lib/pgsql/data/
    fi
}

configure_postgresql() {
    local pg_hba="/var/lib/pgsql/data/pg_hba.conf"
    
    if [ -f "$pg_hba" ]; then
        log_info "Configuring PostgreSQL authentication..."
        cp "$pg_hba" "$pg_hba.backup"
        
        cat > "$pg_hba" <<'EOF'
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             all                                     peer
host    all             all             127.0.0.1/32            md5
host    all             all             ::1/128                 md5
local   replication     all                                     peer
host    replication     all             127.0.0.1/32            md5
host    replication     all             ::1/128                 md5
EOF
    fi
}

start_postgresql() {
    log_info "Starting PostgreSQL service..."
    
    systemctl enable postgresql
    systemctl start postgresql
    
    wait_for_service "postgresql" 10 2
}

create_database() {
    log_info "Creating database and user..."
    
    local db_password=$(generate_password)
    
    # Store password for backend configuration
    echo "DB_PASSWORD=$db_password" > "$APP_DIR/.db_credentials"
    chmod 600 "$APP_DIR/.db_credentials"
    
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$db_password';" 2>/dev/null || true
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || true
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>/dev/null || true
    sudo -u postgres psql -c "ALTER USER $DB_USER CREATEDB;" 2>/dev/null || true
    
    log_success "Database '$DB_NAME' created with user '$DB_USER'"
}