import time

# Simple in-memory rate limiter for LLM requests
# Keeps timestamps of outgoing LLM requests to prevent API bill runaway
LLM_REQUESTS = []

def is_rate_limited(max_requests=10, period=300):
    """
    Returns True if the rate limit is exceeded, False if the request is allowed.
    Default: max 10 requests per 5 minutes (300 seconds).
    """
    global LLM_REQUESTS
    now = time.time()
    # Clean up requests older than the time window
    LLM_REQUESTS = [t for t in LLM_REQUESTS if now - t < period]
    
    if len(LLM_REQUESTS) >= max_requests:
        return True
        
    LLM_REQUESTS.append(now)
    return False
