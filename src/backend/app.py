from flask import Flask, request, jsonify, send_file, send_from_directory, session, render_template_string
import os, xml.etree.ElementTree as ET, base64, subprocess, io, zipfile, shutil, datetime, psycopg2, bcrypt, json, requests, logging, psutil, netaddr
from functools import wraps
import pyrad.packet
import pyrad.client
import xmltodict
import cryptography.x509
from cryptography.hazmat.primitives import serialization
import socket
import threading
import time
import sys
import signal
from contextlib import contextmanager
import logging.handlers

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ================= CONSTANTS =================
CONFIG_FILE = "/opt/kurs-light/config.xml"
CA_DIR = "/opt/kurs-light/ca"
OPENVPN_DIR = "/opt/kurs-light/openvpn"
FRONTEND_DIR = "/opt/kurs-light/frontend"
WEB_PORT = 5000
SSL_DIR = "/opt/kurs-light/ssl"
SSL_CERT = "/opt/kurs-light/ssl/server.crt"
SSL_KEY = "/opt/kurs-light/ssl/server.key"
CERTS_DIR = "/opt/kurs-light/certs"

# Database configuration
DB_CONFIG = {
    'dbname': 'kurslight_db',
    'user': 'kurslight_user',
    'password': 'default_password_123',
    'host': 'localhost'
}

# ================= LOGGING SETUP =================
def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # File handler
    file_handler = logging.FileHandler('/opt/kurs-light/logs/backend.log')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Syslog handler
    try:
        syslog_handler = logging.handlers.SysLogHandler(address='/dev/log', facility='local0')
        syslog_handler.setFormatter(formatter)
        logger.addHandler(syslog_handler)
    except Exception as e:
        print(f"Could not setup syslog: {e}")

setup_logging()
logger = logging.getLogger(__name__)

# ================= DATABASE FUNCTIONS =================
def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def init_db():
    """Initialize database tables"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Users table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(20) DEFAULT 'user',
            full_name VARCHAR(100),
            email VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            last_login TIMESTAMP,
            failed_attempts INTEGER DEFAULT 0,
            locked_until TIMESTAMP
        )
    ''')
    
    # User groups table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_groups (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50) UNIQUE NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            vpn_access BOOLEAN DEFAULT TRUE,
            max_connections INTEGER DEFAULT 5,
            bandwidth_limit INTEGER DEFAULT 0,
            access_hours VARCHAR(100) DEFAULT '00:00-23:59'
        )
    ''')
    
    # User-group association table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_group_membership (
            user_id INTEGER REFERENCES users(id),
            group_id INTEGER REFERENCES user_groups(id),
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, group_id)
        )
    ''')
    
    # User certificates table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_certificates (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            certificate_name VARCHAR(100) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            status VARCHAR(20) DEFAULT 'active',
            vpn_config TEXT,
            revoked_at TIMESTAMP,
            revocation_reason TEXT
        )
    ''')
    
    # VPN instances table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS vpn_instances (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            description TEXT,
            config TEXT,
            status VARCHAR(20) DEFAULT 'stopped',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            port INTEGER DEFAULT 1194,
            protocol VARCHAR(10) DEFAULT 'udp',
            subnet CIDR,
            active_clients INTEGER DEFAULT 0,
            max_clients INTEGER DEFAULT 100
        )
    ''')
    
    # VPN connection logs
    cur.execute('''
        CREATE TABLE IF NOT EXISTS vpn_connection_logs (
            id SERIAL PRIMARY KEY,
            vpn_instance VARCHAR(100),
            username VARCHAR(100),
            client_ip INET,
            client_port INTEGER,
            server_ip INET,
            server_port INTEGER,
            action VARCHAR(20),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            bytes_sent BIGINT DEFAULT 0,
            bytes_received BIGINT DEFAULT 0,
            duration INTERVAL,
            session_id VARCHAR(100)
        )
    ''')
    
    # System audit logs
    cur.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            action VARCHAR(100) NOT NULL,
            resource_type VARCHAR(50),
            resource_id INTEGER,
            details JSONB,
            ip_address INET,
            user_agent TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # RADIUS users table (sync with RADIUS database)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS radius_users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(64) NOT NULL,
            is_radius_enabled BOOLEAN DEFAULT FALSE,
            radius_attributes JSONB,
            last_sync TIMESTAMP,
            UNIQUE(username)
        )
    ''')
    
    # Insert default admin user
    cur.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
    if cur.fetchone()[0] == 0:
        admin_password = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cur.execute(
            "INSERT INTO users (username, password_hash, role, full_name, email) VALUES (%s, %s, %s, %s, %s)",
            ('admin', admin_password, 'admin', 'System Administrator', 'admin@localhost')
        )
    
    # Insert default groups
    default_groups = [
        ('vpn_users', 'Regular VPN users', True, 5, 100, '00:00-23:59'),
        ('admins', 'System administrators', True, 100, 0, '00:00-23:59'),
        ('guests', 'Temporary access users', True, 1, 10, '08:00-20:00'),
        ('restricted', 'Users with limited access', False, 0, 1, '09:00-18:00')
    ]
    
    for group_name, description, vpn_access, max_conn, bandwidth, hours in default_groups:
        cur.execute(
            "INSERT INTO user_groups (name, description, vpn_access, max_connections, bandwidth_limit, access_hours) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (name) DO NOTHING",
            (group_name, description, vpn_access, max_conn, bandwidth, hours)
        )
    
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Database initialized successfully")

# Initialize database on startup
init_db()

# ================= RADIUS INTEGRATION =================
class RadiusClient:
    def __init__(self, server: str, secret: str, port: int = 1812, timeout: int = 5):
        self.server = server
        self.secret = secret
        self.port = port
        self.timeout = timeout
        self.client = None
        
    def _initialize_client(self):
        """Initialize RADIUS client"""
        try:
            self.dictionary = pyrad.dictionary.Dictionary("/etc/raddb/dictionary")
            self.client = pyrad.client.Client(
                server=self.server,
                secret=self.secret.encode('utf-8'),
                dict=self.dictionary,
                port=self.port,
                timeout=self.timeout
            )
        except Exception as e:
            logger.error(f"Failed to initialize RADIUS client: {e}")
            raise
    
    def authenticate(self, username: str, password: str) -> dict:
        """Authenticate user against RADIUS server"""
        if not self.client:
            self._initialize_client()
        
        try:
            req = self.client.CreateAuthPacket(
                code=pyrad.packet.AccessRequest,
                User_Name=username,
                NAS_Identifier="kurs-light-vpn",
                NAS_IP_Address="127.0.0.1"
            )
            req["User-Password"] = req.PwCrypt(password)
            
            response = self.client.SendPacket(req)
            
            if response.code == pyrad.packet.AccessAccept:
                return {"success": True, "message": "Authentication successful"}
            else:
                return {"success": False, "message": "Authentication failed"}
                
        except Exception as e:
            logger.error(f"RADIUS authentication error: {e}")
            return {"success": False, "message": f"RADIUS error: {str(e)}"}

radius_client = None

def initialize_radius(config: dict) -> bool:
    """Initialize RADIUS client with configuration"""
    global radius_client
    try:
        if config.get('enabled', False):
            radius_client = RadiusClient(
                server=config.get('server', 'localhost'),
                secret=config.get('secret', ''),
                port=int(config.get('port', 1812)),
                timeout=int(config.get('timeout', 5))
            )
            logger.info("RADIUS client initialized successfully")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to initialize RADIUS client: {e}")
        return False

def create_radius_user(username: str, password: str) -> bool:
    """Create user in RADIUS database"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Add to RADIUS database
        cur.execute('''
            INSERT INTO radius_users (username, is_radius_enabled, radius_attributes, last_sync)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (username) DO UPDATE SET
                is_radius_enabled = EXCLUDED.is_radius_enabled,
                last_sync = CURRENT_TIMESTAMP
        ''', (username, True, json.dumps({"created": True})))
        
        # Also add to RADIUS check table
        cur.execute("""
            INSERT INTO radcheck (username, attribute, op, value)
            VALUES (%s, 'Cleartext-Password', ':=', %s)
            ON CONFLICT DO NOTHING
        """, (username, password))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"RADIUS user created: {username}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create RADIUS user: {e}")
        return False

# ================= AUTHENTICATION & AUTHORIZATION =================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Authentication required"}), 401
        if session.get('role') != 'admin':
            log_audit_event("UNAUTHORIZED_ACCESS", details={"endpoint": request.endpoint})
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated_function

def check_user_lock(username):
    """Check if user account is locked"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT locked_until FROM users WHERE username = %s", (username,))
    result = cur.fetchone()
    
    cur.close()
    conn.close()
    
    if result and result[0]:
        if result[0] > datetime.datetime.now():
            return True
    return False

def update_login_attempts(username, success):
    """Update user login attempts"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    if success:
        cur.execute('''
            UPDATE users 
            SET failed_attempts = 0, locked_until = NULL, last_login = CURRENT_TIMESTAMP 
            WHERE username = %s
        ''', (username,))
    else:
        cur.execute(
            "UPDATE users SET failed_attempts = failed_attempts + 1 WHERE username = %s RETURNING failed_attempts",
            (username,)
        )
        result = cur.fetchone()
        if result and result[0] >= 5:  # Lock after 5 failed attempts
            lock_time = datetime.datetime.now() + datetime.timedelta(minutes=30)
            cur.execute(
                "UPDATE users SET locked_until = %s WHERE username = %s",
                (lock_time, username)
            )
    
    conn.commit()
    cur.close()
    conn.close()

# ================= AUDIT LOGGING =================
def log_audit_event(action, resource_type=None, resource_id=None, details=None):
    """Log audit event to database"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute('''
            INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (
            session.get('user_id'),
            action,
            resource_type,
            resource_id,
            json.dumps(details) if details else None,
            request.remote_addr,
            request.headers.get('User-Agent')
        ))
        
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to log audit event: {str(e)}")

# ================= AUTHENTICATION ROUTES =================
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    
    # Check if user is locked
    if check_user_lock(username):
        return jsonify({"error": "Account temporarily locked. Try again later."}), 423
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute(
        "SELECT id, username, password_hash, role, full_name, is_active FROM users WHERE username = %s",
        (username,)
    )
    user = cur.fetchone()
    
    if user and user[5] and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
        session['user_id'] = user[0]
        session['username'] = user[1]
        session['role'] = user[3]
        session['full_name'] = user[4]
        
        update_login_attempts(username, True)
        log_audit_event("LOGIN_SUCCESS", details={"username": username})
        
        cur.close()
        conn.close()
        return jsonify({
            "message": "Login successful",
            "user": {
                "id": user[0],
                "username": user[1],
                "role": user[3],
                "full_name": user[4]
            }
        })
    else:
        update_login_attempts(username, False)
        log_audit_event("LOGIN_FAILED", details={"username": username})
        cur.close()
        conn.close()
        return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    log_audit_event("LOGOUT")
    session.clear()
    return jsonify({"message": "Logout successful"})

@app.route('/api/auth/me', methods=['GET'])
@login_required
def get_current_user():
    return jsonify({
        "user": {
            "id": session['user_id'],
            "username": session['username'],
            "role": session['role'],
            "full_name": session.get('full_name', '')
        }
    })

@app.route('/api/auth/change-password', methods=['POST'])
@login_required
def change_password():
    data = request.json
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not current_password or not new_password:
        return jsonify({"error": "Current and new password required"}), 400
    
    if len(new_password) < 8:
        return jsonify({"error": "New password must be at least 8 characters long"}), 400
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute(
        "SELECT password_hash FROM users WHERE id = %s",
        (session['user_id'],)
    )
    user = cur.fetchone()
    
    if not user or not bcrypt.checkpw(current_password.encode('utf-8'), user[0].encode('utf-8')):
        cur.close()
        conn.close()
        return jsonify({"error": "Current password is incorrect"}), 400
    
    new_password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    cur.execute(
        "UPDATE users SET password_hash = %s WHERE id = %s",
        (new_password_hash, session['user_id'])
    )
    
    conn.commit()
    cur.close()
    conn.close()
    
    log_audit_event("PASSWORD_CHANGE")
    return jsonify({"message": "Password changed successfully"})

# ================= USER MANAGEMENT ROUTES =================
@app.route('/api/users', methods=['GET'])
@admin_required
def get_users():
    """Get all users with their groups"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        SELECT 
            u.id, u.username, u.role, u.full_name, u.email, 
            u.created_at, u.is_active, u.last_login,
            COALESCE(json_agg(DISTINCT g.name) FILTER (WHERE g.name IS NOT NULL), '[]') as groups,
            COUNT(DISTINCT uc.id) as certificate_count,
            ru.is_radius_enabled
        FROM users u
        LEFT JOIN user_group_membership ugm ON u.id = ugm.user_id
        LEFT JOIN user_groups g ON ugm.group_id = g.id
        LEFT JOIN user_certificates uc ON u.id = uc.user_id AND uc.status = 'active'
        LEFT JOIN radius_users ru ON u.username = ru.username
        GROUP BY u.id, ru.is_radius_enabled
        ORDER BY u.created_at DESC
    ''')
    
    users = []
    for row in cur.fetchall():
        users.append({
            'id': row[0],
            'username': row[1],
            'role': row[2],
            'full_name': row[3],
            'email': row[4],
            'created_at': row[5].isoformat(),
            'is_active': row[6],
            'last_login': row[7].isoformat() if row[7] else None,
            'groups': row[8],
            'certificate_count': row[9],
            'radius_enabled': row[10] if row[10] is not None else False
        })
    
    cur.close()
    conn.close()
    return jsonify(users)

@app.route('/api/users', methods=['POST'])
@admin_required
def create_user():
    """Create new user"""
    data = request.json
    
    # Validation
    required_fields = ['username', 'password', 'role']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    if len(data['password']) < 8:
        return jsonify({"error": "Password must be at least 8 characters long"}), 400
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Check if username exists
        cur.execute("SELECT id FROM users WHERE username = %s", (data['username'],))
        if cur.fetchone():
            return jsonify({"error": "Username already exists"}), 400
        
        # Hash password
        password_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create user
        cur.execute('''
            INSERT INTO users (username, password_hash, role, full_name, email, is_active) 
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
        ''', (
            data['username'], 
            password_hash, 
            data['role'],
            data.get('full_name', ''),
            data.get('email', ''),
            data.get('is_active', True)
        ))
        user_id = cur.fetchone()[0]
        
        # Add to groups
        if 'groups' in data and isinstance(data['groups'], list):
            for group_name in data['groups']:
                cur.execute("SELECT id FROM user_groups WHERE name = %s", (group_name,))
                group = cur.fetchone()
                if group:
                    cur.execute(
                        "INSERT INTO user_group_membership (user_id, group_id) VALUES (%s, %s)",
                        (user_id, group[0])
                    )
        
        # Create RADIUS entry if enabled
        if data.get('create_radius_account', False):
            create_radius_user(data['username'], data['password'])
        
        conn.commit()
        
        log_audit_event("USER_CREATE", "user", user_id, {
            "username": data['username'], 
            "role": data['role'],
            "groups": data.get('groups', [])
        })
        
        return jsonify({
            "message": "User created successfully", 
            "user_id": user_id
        })
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to create user: {str(e)}")
        return jsonify({"error": f"Failed to create user: {str(e)}"}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user(user_id):
    """Get specific user details"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        SELECT 
            u.id, u.username, u.role, u.full_name, u.email, 
            u.created_at, u.is_active, u.last_login, u.failed_attempts,
            COALESCE(json_agg(DISTINCT g.name) FILTER (WHERE g.name IS NOT NULL), '[]') as groups,
            ru.is_radius_enabled
        FROM users u
        LEFT JOIN user_group_membership ugm ON u.id = ugm.user_id
        LEFT JOIN user_groups g ON ugm.group_id = g.id
        LEFT JOIN radius_users ru ON u.username = ru.username
        WHERE u.id = %s
        GROUP BY u.id, ru.is_radius_enabled
    ''', (user_id,))
    
    user = cur.fetchone()
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    user_data = {
        'id': user[0],
        'username': user[1],
        'role': user[2],
        'full_name': user[3],
        'email': user[4],
        'created_at': user[5].isoformat(),
        'is_active': user[6],
        'last_login': user[7].isoformat() if user[7] else None,
        'failed_attempts': user[8],
        'groups': user[9],
        'radius_enabled': user[10] if user[10] is not None else False
    }
    
    cur.close()
    conn.close()
    return jsonify(user_data)

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    """Update user information"""
    data = request.json
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Check if user exists and is not the main admin
        cur.execute("SELECT username, role FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        if user[0] == 'admin' and data.get('role') != 'admin':
            return jsonify({"error": "Cannot change admin user role"}), 400
        
        update_fields = []
        update_values = []
        
        if 'full_name' in data:
            update_fields.append("full_name = %s")
            update_values.append(data['full_name'])
        if 'email' in data:
            update_fields.append("email = %s")
            update_values.append(data['email'])
        if 'role' in data:
            update_fields.append("role = %s")
            update_values.append(data['role'])
        if 'is_active' in data:
            update_fields.append("is_active = %s")
            update_values.append(data['is_active'])
        
        if update_fields:
            update_values.append(user_id)
            cur.execute(
                f"UPDATE users SET {', '.join(update_fields)} WHERE id = %s",
                update_values
            )
        
        # Update groups
        if 'groups' in data:
            cur.execute("DELETE FROM user_group_membership WHERE user_id = %s", (user_id,))
            
            for group_name in data['groups']:
                cur.execute("SELECT id FROM user_groups WHERE name = %s", (group_name,))
                group = cur.fetchone()
                if group:
                    cur.execute(
                        "INSERT INTO user_group_membership (user_id, group_id) VALUES (%s, %s)",
                        (user_id, group[0])
                    )
        
        # Update RADIUS status
        if 'radius_enabled' in data:
            if data['radius_enabled']:
                # Get user password to create RADIUS account
                cur.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))
                password_hash = cur.fetchone()[0]
                # Note: In production, you'd need to store plain text passwords or use different auth
                create_radius_user(user[0], "temporary_password")
            else:
                # Disable RADIUS
                cur.execute("UPDATE radius_users SET is_radius_enabled = FALSE WHERE username = %s", (user[0],))
        
        conn.commit()
        
        log_audit_event("USER_UPDATE", "user", user_id, data)
        return jsonify({"message": "User updated successfully"})
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to update user: {str(e)}")
        return jsonify({"error": f"Failed to update user: {str(e)}"}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """Delete user"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT username FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        if user[0] == 'admin':
            return jsonify({"error": "Cannot delete admin user"}), 400
        
        # Remove from groups
        cur.execute("DELETE FROM user_group_membership WHERE user_id = %s", (user_id,))
        
        # Disable RADIUS account
        cur.execute("UPDATE radius_users SET is_radius_enabled = FALSE WHERE username = %s", (user[0],))
        
        # Delete user certificates
        cur.execute("DELETE FROM user_certificates WHERE user_id = %s", (user_id,))
        
        # Delete user
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        
        conn.commit()
        
        log_audit_event("USER_DELETE", "user", user_id, {"username": user[0]})
        return jsonify({"message": "User deleted successfully"})
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to delete user: {str(e)}")
        return jsonify({"error": f"Failed to delete user: {str(e)}"}), 500
    finally:
        cur.close()
        conn.close()

# ================= GROUP MANAGEMENT ROUTES =================
@app.route('/api/groups', methods=['GET'])
@admin_required
def get_groups():
    """Get all groups with user counts"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        SELECT 
            g.id, g.name, g.description, g.created_at, 
            g.vpn_access, g.max_connections, g.bandwidth_limit, g.access_hours,
            COUNT(ugm.user_id) as user_count
        FROM user_groups g
        LEFT JOIN user_group_membership ugm ON g.id = ugm.group_id
        GROUP BY g.id
        ORDER BY g.name
    ''')
    
    groups = []
    for row in cur.fetchall():
        groups.append({
            'id': row[0],
            'name': row[1],
            'description': row[2],
            'created_at': row[3].isoformat(),
            'vpn_access': row[4],
            'max_connections': row[5],
            'bandwidth_limit': row[6],
            'access_hours': row[7],
            'user_count': row[8]
        })
    
    cur.close()
    conn.close()
    return jsonify(groups)

@app.route('/api/groups', methods=['POST'])
@admin_required
def create_group():
    """Create new user group"""
    data = request.json
    
    if 'name' not in data:
        return jsonify({"error": "Group name is required"}), 400
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute(
            "INSERT INTO user_groups (name, description, vpn_access, max_connections, bandwidth_limit, access_hours) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (
                data['name'],
                data.get('description', ''),
                data.get('vpn_access', True),
                data.get('max_connections', 5),
                data.get('bandwidth_limit', 0),
                data.get('access_hours', '00:00-23:59')
            )
        )
        group_id = cur.fetchone()[0]
        
        conn.commit()
        
        log_audit_event("GROUP_CREATE", "group", group_id, data)
        return jsonify({"message": "Group created successfully", "group_id": group_id})
        
    except psycopg2.IntegrityError:
        conn.rollback()
        return jsonify({"error": "Group name already exists"}), 400
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to create group: {str(e)}")
        return jsonify({"error": f"Failed to create group: {str(e)}"}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/groups/<int:group_id>', methods=['GET'])
@admin_required
def get_group(group_id):
    """Get specific group details"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        SELECT 
            g.id, g.name, g.description, g.created_at, 
            g.vpn_access, g.max_connections, g.bandwidth_limit, g.access_hours,
            COALESCE(json_agg(DISTINCT u.username) FILTER (WHERE u.username IS NOT NULL), '[]') as users
        FROM user_groups g
        LEFT JOIN user_group_membership ugm ON g.id = ugm.group_id
        LEFT JOIN users u ON ugm.user_id = u.id
        WHERE g.id = %s
        GROUP BY g.id
    ''', (group_id,))
    
    group = cur.fetchone()
    if not group:
        return jsonify({"error": "Group not found"}), 404
    
    group_data = {
        'id': group[0],
        'name': group[1],
        'description': group[2],
        'created_at': group[3].isoformat(),
        'vpn_access': group[4],
        'max_connections': group[5],
        'bandwidth_limit': group[6],
        'access_hours': group[7],
        'users': group[8]
    }
    
    cur.close()
    conn.close()
    return jsonify(group_data)

@app.route('/api/groups/<int:group_id>', methods=['PUT'])
@admin_required
def update_group(group_id):
    """Update group information"""
    data = request.json
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        update_fields = []
        update_values = []
        
        if 'description' in data:
            update_fields.append("description = %s")
            update_values.append(data['description'])
        if 'vpn_access' in data:
            update_fields.append("vpn_access = %s")
            update_values.append(data['vpn_access'])
        if 'max_connections' in data:
            update_fields.append("max_connections = %s")
            update_values.append(data['max_connections'])
        if 'bandwidth_limit' in data:
            update_fields.append("bandwidth_limit = %s")
            update_values.append(data['bandwidth_limit'])
        if 'access_hours' in data:
            update_fields.append("access_hours = %s")
            update_values.append(data['access_hours'])
        
        if update_fields:
            update_values.append(group_id)
            cur.execute(
                f"UPDATE user_groups SET {', '.join(update_fields)} WHERE id = %s",
                update_values
            )
            
            if cur.rowcount == 0:
                return jsonify({"error": "Group not found"}), 404
        
        conn.commit()
        
        log_audit_event("GROUP_UPDATE", "group", group_id, data)
        return jsonify({"message": "Group updated successfully"})
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to update group: {str(e)}")
        return jsonify({"error": f"Failed to update group: {str(e)}"}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/groups/<int:group_id>', methods=['DELETE'])
@admin_required
def delete_group(group_id):
    """Delete user group"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Check if group exists and is not a default group
        cur.execute("SELECT name FROM user_groups WHERE id = %s", (group_id,))
        group = cur.fetchone()
        if not group:
            return jsonify({"error": "Group not found"}), 404
        
        default_groups = ['vpn_users', 'admins', 'guests', 'restricted']
        if group[0] in default_groups:
            return jsonify({"error": "Cannot delete default groups"}), 400
        
        # Remove group membership
        cur.execute("DELETE FROM user_group_membership WHERE group_id = %s", (group_id,))
        
        # Delete group
        cur.execute("DELETE FROM user_groups WHERE id = %s", (group_id,))
        
        conn.commit()
        
        log_audit_event("GROUP_DELETE", "group", group_id, {"name": group[0]})
        return jsonify({"message": "Group deleted successfully"})
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to delete group: {str(e)}")
        return jsonify({"error": f"Failed to delete group: {str(e)}"}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/groups/<int:group_id>/users', methods=['GET'])
@admin_required
def get_group_users(group_id):
    """Get users in a specific group"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        SELECT 
            u.id, u.username, u.role, u.full_name, u.email, u.is_active,
            ugm.assigned_at
        FROM users u
        JOIN user_group_membership ugm ON u.id = ugm.user_id
        WHERE ugm.group_id = %s
        ORDER BY u.username
    ''', (group_id,))
    
    users = []
    for row in cur.fetchall():
        users.append({
            'id': row[0],
            'username': row[1],
            'role': row[2],
            'full_name': row[3],
            'email': row[4],
            'is_active': row[5],
            'assigned_at': row[6].isoformat()
        })
    
    cur.close()
    conn.close()
    return jsonify(users)

# ================= VPN INSTANCES MANAGEMENT =================
def get_vpn_status(instance_name):
    """Get VPN instance status by checking running processes"""
    try:
        conf_path = os.path.join(OPENVPN_DIR, 'servers', instance_name, 'server.conf')
        result = subprocess.run(['pgrep', '-f', f'openvpn.*{conf_path}'], 
                              capture_output=True, text=True)
        return 'running' if result.stdout.strip() else 'stopped'
    except:
        return 'unknown'

@app.route('/api/vpn-instances', methods=['GET'])
@login_required
def get_vpn_instances():
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        SELECT id, name, description, status, port, protocol, subnet, active_clients, max_clients, created_at
        FROM vpn_instances
        ORDER BY created_at DESC
    ''')
    
    instances = []
    for row in cur.fetchall():
        # Update status based on actual process
        current_status = get_vpn_status(row[1])
        if current_status != row[3]:
            cur.execute(
                "UPDATE vpn_instances SET status = %s WHERE id = %s",
                (current_status, row[0])
            )
            status = current_status
        else:
            status = row[3]
        
        instances.append({
            'id': row[0],
            'name': row[1],
            'description': row[2],
            'status': status,
            'port': row[4],
            'protocol': row[5],
            'subnet': row[6],
            'active_clients': row[7],
            'max_clients': row[8],
            'created_at': row[9].isoformat()
        })
    
    conn.commit()
    cur.close()
    conn.close()
    
    return jsonify(instances)

# ================= CERTIFICATES MANAGEMENT =================
def find_easyrsa():
    """Find easyrsa executable"""
    paths = [
        f"{CA_DIR}/easyrsa",
        f"{CA_DIR}/3/easyrsa",
        "/usr/bin/easyrsa",
        "/usr/share/easy-rsa/easyrsa"
    ]
    for path in paths:
        if os.path.exists(path):
            return path
    return None

@app.route('/api/certs', methods=['GET'])
@login_required
def get_certificates():
    conn = get_db_connection()
    cur = conn.cursor()
    
    if session.get('role') == 'admin':
        cur.execute('''
            SELECT uc.id, uc.certificate_name, uc.created_at, uc.expires_at, uc.status,
                   u.username, uc.revoked_at, uc.revocation_reason
            FROM user_certificates uc
            JOIN users u ON uc.user_id = u.id
            ORDER BY uc.created_at DESC
        ''')
    else:
        cur.execute('''
            SELECT id, certificate_name, created_at, expires_at, status, revoked_at, revocation_reason
            FROM user_certificates 
            WHERE user_id = %s 
            ORDER BY created_at DESC
        ''', (session['user_id'],))
    
    certificates = []
    for row in cur.fetchall():
        cert_data = {
            'id': row[0],
            'name': row[1],
            'created': row[2].isoformat(),
            'expires': row[3].isoformat() if row[3] else None,
            'status': row[4],
            'revoked_at': row[6].isoformat() if row[6] else None,
            'revocation_reason': row[7]
        }
        
        if session.get('role') == 'admin':
            cert_data['username'] = row[5]
        
        certificates.append(cert_data)
    
    cur.close()
    conn.close()
    
    return jsonify(certificates)

# ================= SYSTEM INFO & MONITORING =================
@app.route('/api/system/info', methods=['GET'])
@login_required
def get_system_info():
    try:
        # System load
        load_avg = os.getloadavg()
        
        # Memory info
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Disk usage
        disk = psutil.disk_usage('/')
        
        # Network info
        net_io = psutil.net_io_counters()
        
        # VPN processes
        vpn_processes = len([p for p in psutil.process_iter(['name']) 
                           if 'openvpn' in p.info['name'] or 'openvpn' in ' '.join(p.cmdline())])
        
        # Database connections
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM pg_stat_activity")
        db_connections = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM vpn_instances WHERE status = 'running'")
        active_vpns = cur.fetchone()[0]
        
        cur.execute('''
            SELECT COUNT(*) FROM user_certificates 
            WHERE status = 'active' AND expires_at > CURRENT_TIMESTAMP
        ''')
        active_certs = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM users WHERE is_active = true")
        active_users = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM user_groups")
        total_groups = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        return jsonify({
            "system": {
                "load_average": [round(load, 2) for load in load_avg],
                "cpu_cores": psutil.cpu_count(),
                "uptime": int(time.time() - psutil.boot_time())
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percent": memory.percent
            },
            "swap": {
                "total": swap.total,
                "used": swap.used,
                "percent": swap.percent
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent
            },
            "network": {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv
            },
            "services": {
                "active_vpn_instances": active_vpns,
                "vpn_processes": vpn_processes,
                "database_connections": db_connections,
                "active_certificates": active_certs,
                "active_users": active_users,
                "total_groups": total_groups
            },
            "timestamp": datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get system info: {str(e)}")
        return jsonify({"error": f"Failed to get system info: {str(e)}"}), 500

@app.route('/api/system/audit-logs', methods=['GET'])
@admin_required
def get_audit_logs():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        offset = (page - 1) * per_page
        
        cur.execute('''
            SELECT al.id, u.username, al.action, al.resource_type, al.resource_id, 
                   al.details, al.ip_address, al.timestamp
            FROM audit_logs al
            LEFT JOIN users u ON al.user_id = u.id
            ORDER BY al.timestamp DESC
            LIMIT %s OFFSET %s
        ''', (per_page, offset))
        
        logs = []
        for row in cur.fetchall():
            logs.append({
                'id': row[0],
                'username': row[1],
                'action': row[2],
                'resource_type': row[3],
                'resource_id': row[4],
                'details': row[5],
                'ip_address': row[6],
                'timestamp': row[7].isoformat()
            })
        
        cur.close()
        conn.close()
        
        return jsonify(logs)
        
    except Exception as e:
        logger.error(f"Failed to get audit logs: {str(e)}")
        return jsonify({"error": f"Failed to get audit logs: {str(e)}"}), 500

# ================= CONFIGURATION MANAGEMENT =================
def load_xml():
    """Load XML configuration file"""
    if not os.path.exists(CONFIG_FILE):
        return None, None
    tree = ET.parse(CONFIG_FILE)
    return tree, tree.getroot()

def save_xml(tree):
    """Save XML configuration file"""
    tree.write(CONFIG_FILE, encoding='UTF-8', xml_declaration=True)

@app.route('/api/config/radius', methods=['GET'])
@admin_required
def get_radius_config():
    tree, root = load_xml()
    if not root:
        return jsonify({"error": "Configuration file not found"}), 500
    
    radius_elem = root.find('radius_config')
    if radius_elem is None:
        return jsonify({"error": "Radius configuration not found"}), 404
    
    return jsonify({
        'enabled': radius_elem.find('enabled').text.lower() == 'true' if radius_elem.find('enabled') is not None else False,
        'server': radius_elem.find('server').text if radius_elem.find('server') is not None else '',
        'port': radius_elem.find('port').text if radius_elem.find('port') is not None else '1812',
        'secret': radius_elem.find('secret').text if radius_elem.find('secret') is not None else '',
        'timeout': radius_elem.find('timeout').text if radius_elem.find('timeout') is not None else '5',
        'retries': radius_elem.find('retries').text if radius_elem.find('retries') is not None else '3'
    })

@app.route('/api/config/radius', methods=['POST'])
@admin_required
def update_radius_config():
    data = request.json
    tree, root = load_xml()
    if not root:
        return jsonify({"error": "Configuration file not found"}), 500
    
    radius_elem = root.find('radius_config')
    if radius_elem is None:
        radius_elem = ET.SubElement(root, 'radius_config')
    
    for key, value in data.items():
        elem = radius_elem.find(key)
        if elem is None:
            ET.SubElement(radius_elem, key).text = str(value)
        else:
            elem.text = str(value)
    
    save_xml(tree)
    
    # Initialize RADIUS client if enabled
    if data.get('enabled', False):
        initialize_radius(data)
    
    log_audit_event("CONFIG_UPDATE", "radius", None, data)
    return jsonify({"message": "Radius configuration updated successfully"})

# ================= STATIC FILE SERVING =================
@app.route('/')
def serve_index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(FRONTEND_DIR, path)

# ================= ERROR HANDLERS =================
@app.errorhandler(404)
def not_found(error):
    if request.path.startswith('/api/'):
        return jsonify({"error": "Endpoint not found"}), 404
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(403)
def forbidden(error):
    return jsonify({"error": "Access forbidden"}), 403

@app.errorhandler(401)
def unauthorized(error):
    return jsonify({"error": "Authentication required"}), 401

# ================= BACKGROUND TASKS =================
def cleanup_expired_certificates():
    """Background task to clean up expired certificates"""
    while True:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute('''
                UPDATE user_certificates 
                SET status = 'expired' 
                WHERE expires_at < CURRENT_TIMESTAMP AND status = 'active'
            ''')
            
            conn.commit()
            cur.close()
            conn.close()
            
            logger.info("Expired certificates cleanup completed")
            time.sleep(3600)  # Run every hour
            
        except Exception as e:
            logger.error(f"Certificate cleanup error: {str(e)}")
            time.sleep(300)  # Wait 5 minutes on error

def update_vpn_stats():
    """Background task to update VPN statistics"""
    while True:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Get all running VPN instances
            cur.execute("SELECT name FROM vpn_instances WHERE status = 'running'")
            instances = cur.fetchall()
            
            for (instance_name,) in instances:
                # Parse status file to get active clients
                status_file = os.path.join(OPENVPN_DIR, 'servers', instance_name, 'status.log')
                active_clients = 0
                
                if os.path.exists(status_file):
                    try:
                        with open(status_file, 'r') as f:
                            for line in f:
                                if line.startswith('CLIENT_LIST'):
                                    active_clients += 1
                    except:
                        pass
                
                cur.execute(
                    "UPDATE vpn_instances SET active_clients = %s WHERE name = %s",
                    (active_clients, instance_name)
                )
            
            conn.commit()
            cur.close()
            conn.close()
            
            time.sleep(30)  # Update every 30 seconds
            
        except Exception as e:
            logger.error(f"VPN stats update error: {str(e)}")
            time.sleep(60)  # Wait 1 minute on error

# ================= MAIN =================
if __name__ == '__main__':
    # Ensure required directories exist
    os.makedirs(OPENVPN_DIR, exist_ok=True)
    os.makedirs(os.path.join(OPENVPN_DIR, 'servers'), exist_ok=True)
    os.makedirs(CA_DIR, exist_ok=True)
    os.makedirs(SSL_DIR, exist_ok=True)
    os.makedirs(CERTS_DIR, exist_ok=True)
    
    # Start background tasks
    cleanup_thread = threading.Thread(target=cleanup_expired_certificates, daemon=True)
    cleanup_thread.start()
    
    stats_thread = threading.Thread(target=update_vpn_stats, daemon=True)
    stats_thread.start()
    
    logger.info("Starting KursLight VPN Management System")
    
    # Run the application
    context = (SSL_CERT, SSL_KEY)
    app.run(
        host='0.0.0.0',
        port=WEB_PORT,
        ssl_context=context,
        threaded=True,
        debug=False
    )
    # ================= BACKUP MANAGEMENT =================
@app.route('/api/backups', methods=['GET'])
@admin_required
def get_backups():
    """Get list of backups"""
    try:
        manager = BackupManager()
        backups = manager.list_backups()
        return jsonify(backups)
    except Exception as e:
        logger.error(f"Failed to list backups: {str(e)}")
        return jsonify({"error": f"Failed to list backups: {str(e)}"}), 500

@app.route('/api/backups/create', methods=['POST'])
@admin_required
def create_backup():
    """Create a new backup"""
    try:
        manager = BackupManager()
        result = manager.create_backup()
        
        if result['success']:
            log_audit_event("BACKUP_CREATE", details=result)
            return jsonify({"message": "Backup created successfully", "archive": result['archive']})
        else:
            return jsonify({"error": result['error"]}), 500
    except Exception as e:
        logger.error(f"Failed to create backup: {str(e)}")
        return jsonify({"error": f"Failed to create backup: {str(e)}"}), 500

@app.route('/api/backups/<backup_name>/restore', methods=['POST'])
@admin_required
def restore_backup(backup_name):
    """Restore from backup"""
    try:
        # Внимание: это опасная операция, нужно подтверждение
        manager = BackupManager()
        result = manager.restore_backup(backup_name)
        
        if result['success']:
            log_audit_event("BACKUP_RESTORE", details={"backup": backup_name})
            return jsonify({"message": "Backup restored successfully"})
        else:
            return jsonify({"error": result['error']}), 500
    except Exception as e:
        logger.error(f"Failed to restore backup: {str(e)}")
        return jsonify({"error": f"Failed to restore backup: {str(e)}"}), 500

@app.route('/api/backups/<backup_name>', methods=['DELETE'])
@admin_required
def delete_backup(backup_name):
    """Delete a backup"""
    try:
        backup_path = BackupManager().backup_dir / backup_name
        if backup_path.exists():
            backup_path.unlink()
            log_audit_event("BACKUP_DELETE", details={"backup": backup_name})
            return jsonify({"message": "Backup deleted successfully"})
        else:
            return jsonify({"error": "Backup not found"}), 404
    except Exception as e:
        logger.error(f"Failed to delete backup: {str(e)}")
        return jsonify({"error": f"Failed to delete backup: {str(e)}"}), 500