"""
Flask-Caching Configuration
Redis cache layer for scalability
"""
from flask_caching import Cache

# Cache initialization
cache = Cache()

def init_cache(app):
    """Initialize cache with app"""
    
    # Redis cache config
    cache_config = {
        'CACHE_TYPE': 'redis',
        'CACHE_REDIS_URL': app.config.get('REDIS_URL', 'redis://localhost:6379/0'),
        'CACHE_DEFAULT_TIMEOUT': 300,  # 5 minutes
        'CACHE_KEY_PREFIX': 'tevkil_'
    }
    
    cache.init_app(app, config=cache_config)
    app.cache = cache
    
    print("✅ Redis cache initialized")
    return cache

# Cache decorators for common queries
def cache_conversation_list(user_id):
    """Cache key for conversation list"""
    return f"conversations_user_{user_id}"

def cache_online_status(user_id):
    """Cache key for online status"""
    return f"online_status_{user_id}"

def cache_unread_count(user_id):
    """Cache key for unread message count"""
    return f"unread_count_{user_id}"
