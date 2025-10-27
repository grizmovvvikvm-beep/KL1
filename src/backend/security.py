import time
from functools import wraps
from flask import request, jsonify
import pyotp
import qrcode
import io
import base64

# Rate limiting
class RateLimiter:
    def __init__(self):
        self.requests = {}
    
    def is_limited(self, key, limit=100, window=60):
        now = time.time()
        if key not in self.requests:
            self.requests[key] = []
        
        # Remove old requests
        self.requests[key] = [req_time for req_time in self.requests[key] if now - req_time < window]
        
        if len(self.requests[key]) >= limit:
            return True
        
        self.requests[key].append(now)
        return False

rate_limiter = RateLimiter()

def rate_limit(limit=100, window=60):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            key = f"{request.remote_addr}_{request.endpoint}"
            if rate_limiter.is_limited(key, limit, window):
                return jsonify({"error": "Rate limit exceeded"}), 429
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# 2FA Support
def setup_2fa(user_id):
    """Setup 2FA for user"""
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    
    # Generate QR code
    uri = totp.provisioning_uri(f"user{user_id}@kurslight", issuer_name="KursLight VPN")
    qr = qrcode.make(uri)
    
    buffered = io.BytesIO()
    qr.save(buffered, format="PNG")
    qr_code = base64.b64encode(buffered.getvalue()).decode()
    
    return {"secret": secret, "qr_code": qr_code}

def verify_2fa(secret, token):
    """Verify 2FA token"""
    totp = pyotp.TOTP(secret)
    return totp.verify(token)

# Password policy
def validate_password(password):
    """Validate password against policy"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    
    return True, "Password is valid"