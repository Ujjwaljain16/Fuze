from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Global limiter instance to be shared across blueprints
# Configuration is handled in middleware/rate_limiting.py during init_app
limiter = Limiter(key_func=get_remote_address)
