#!/bin/bash

create_backend() {
    log_info "Creating backend application..."
    
    create_virtualenv
    install_python_dependencies
    create_application_code
    create_systemd_service
    setup_database_schema
    
    log_success "Backend application created"
}

create_virtualenv() {
    log_info "Creating Python virtual environment..."
    
    if ! python3 -m venv "$VENV_DIR"; then
        log_warning "Virtual environment creation failed, installing virtualenv..."
        pip3 install virtualenv
        virtualenv "$VENV_DIR"
    fi
    
    # Upgrade pip
    "$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel
}

install_python_dependencies() {
    log_info "Installing Python dependencies..."
    
    # Create requirements.txt
    cat > "$BACKEND_DIR/requirements.txt" <<'REQ'
Flask==2.3.3
Werkzeug==2.3.7
psycopg2-binary==2.9.7
pyrad==2.1
bcrypt==4.0.1
Jinja2==3.1.2
requests==2.31.0
cryptography==41.0.7
xmltodict==0.13.0
pyOpenSSL==23.2.0
netaddr==0.8.0
psutil==5.9.5
gunicorn==21.2.0
python-dateutil==2.8.2
pyyaml==6.0.1
sqlalchemy==2.0.23
alembic==1.12.1
REQ

    "$VENV_DIR/bin/pip" install -r "$BACKEND_DIR/requirements.txt"
}

create_application_code() {
    log_info "Creating application code..."
    
    # Copy the main app.py from src/backend/
    if [ -f "./src/backend/app.py" ]; then
        cp "./src/backend/app.py" "$BACKEND_DIR/"
    else
        log_warning "app.py not found in src, using embedded version"
        # Здесь будет встроенная версия app.py как в оригинальном скрипте
        create_embedded_app_py
    fi
    
    # Create database configuration
    local db_password=$(grep "DB_PASSWORD" "$APP_DIR/.db_credentials" | cut -d= -f2)
    
    cat > "$BACKEND_DIR/database.conf" <<DBCONF
{
    "dbname": "$DB_NAME",
    "user": "$DB_USER", 
    "password": "$db_password",
    "host": "localhost",
    "port": 5432
}
DBCONF

    chmod 600 "$BACKEND_DIR/database.conf"
}

create_embedded_app_py() {
    # Это сокращенная версия - в реальном проекте файл будет полным
    cat > "$BACKEND_DIR/app.py" <<'PY'
from flask import Flask
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

@app.route('/')
def hello():
    return "KursLight VPN Management System"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, ssl_context=('/opt/kurs-light/ssl/server.crt', '/opt/kurs-light/ssl/server.key'))
PY
}

create_systemd_service() {
    log_info "Creating systemd service..."
    
    cat > "/etc/systemd/system/$APP_NAME.service" <<SERVICE
[Unit]
Description=KursLight VPN Management System
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=$BACKEND_DIR
Environment=PATH=$VENV_DIR/bin
Environment=PYTHONPATH=$BACKEND_DIR
ExecStart=$VENV_DIR/bin/python app.py
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# Security
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=$APP_DIR
ReadWritePaths=/var/lib/postgresql
ReadWritePaths=/var/log

[Install]
WantedBy=multi-user.target
SERVICE
}

setup_database_schema() {
    log_info "Setting up database schema..."
    
    # This will be executed when the application first starts
    # The application contains the init_db() function
    log_info "Database schema will be initialized on first application start"
}