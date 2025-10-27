import time
from functools import wraps
from flask import request, jsonify
from collections import defaultdict
import redis
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self):
        # In production, use Redis. For development, use memory.
        try:
            self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
            self.use_redis = True
        except:
            self.use_redis = False
            self.memory_store = defaultdict(list)
        
        self.limits = {
            "auth": {"limit": 5, "window": 300},      # 5 attempts per 5 minutes
            "api": {"limit": 100, "window": 900},     # 100 requests per 15 minutes  
            "vpn_operations": {"limit": 10, "window": 60},  # 10 operations per minute
            "cert_operations": {"limit": 5, "window": 60},  # 5 operations per minute
        }
    
    def is_rate_limited(self, key: str, limit_type: str) -> bool:
        """Check if request should be rate limited"""
        if limit_type not in self.limits:
            return False
        
        limit_config = self.limits[limit_type]
        current_time = time.time()
        
        if self.use_redis:
            return self._redis_check(key, limit_config, current_time)
        else:
            return self._memory_check(key, limit_config, current_time)
    
    def _redis_check(self, key: str, limit_config: dict, current_time: float) -> bool:
        """Redis-based rate limiting"""
        try:
            redis_key = f"rate_limit:{key}"
            
            # Remove old timestamps
            self.redis_client.zremrangebyscore(redis_key, 0, current_time - limit_config["window"])
            
            # Count recent requests
            request_count = self.redis_client.zcard(redis_key)
            
            if request_count >= limit_config["limit"]:
                return True
            
            # Add current request
            self.redis_client.zadd(redis_key, {str(current_time): current_time})
            self.redis_client.expire(redis_key, limit_config["window"])
            
            return False
            
        except Exception as e:
            logger.error(f"Redis rate limiting error: {e}")
            return False
    
    def _memory_check(self, key: str, limit_config: dict, current_time: float) -> bool:
        """Memory-based rate limiting"""
        window_start = current_time - limit_config["window"]
        
        # Remove old timestamps
        self.memory_store[key] = [
            ts for ts in self.memory_store[key] 
            if ts > window_start
        ]
        
        if len(self.memory_store[key]) >= limit_config["limit"]:
            return True
        
        # Add current request
        self.memory_store[key].append(current_time)
        return False
    
    def get_remaining_requests(self, key: str, limit_type: str) -> int:
        """Get number of remaining requests"""
        if limit_type not in self.limits:
            return 0
        
        limit_config = self.limits[limit_type]
        current_time = time.time()
        
        if self.use_redis:
            redis_key = f"rate_limit:{key}"
            self.redis_client.zremrangebyscore(redis_key, 0, current_time - limit_config["window"])
            request_count = self.redis_client.zcard(redis_key)
        else:
            window_start = current_time - limit_config["window"]
            request_count = len([
                ts for ts in self.memory_store[key] 
                if ts > window_start
            ])
        
        return max(0, limit_config["limit"] - request_count)

def rate_limit(limit_type: str):
    """Decorator for rate limiting API endpoints"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Create rate limit key
            if hasattr(request, 'user_id'):
                key = f"{limit_type}:{request.user_id}"
            else:
                key = f"{limit_type}:{request.remote_addr}"
            
            limiter = RateLimiter()
            
            if limiter.is_rate_limited(key, limit_type):
                remaining = limiter.get_remaining_requests(key, limit_type)
                return jsonify({
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Try again later.",
                    "retry_after": 60,
                    "remaining": remaining
                }), 429
            
            # Add rate limit headers
            response = f(*args, **kwargs)
            
            if hasattr(response, 'headers'):
                remaining = limiter.get_remaining_requests(key, limit_type)
                response.headers['X-RateLimit-Limit'] = str(limiter.limits[limit_type]["limit"])
                response.headers['X-RateLimit-Remaining'] = str(remaining)
                response.headers['X-RateLimit-Reset'] = str(int(time.time() + limiter.limits[limit_type]["window"]))
            
            return response
        return decorated_function
    return decorator

# Global rate limiter instance
rate_limiter = RateLimiter()