from django.core.cache import cache


def consume_otp_authorization(target, purpose):
    limit_key = f"otp_consume_limit:{purpose}:{target}"
    cache.add(limit_key, 0, timeout=20)
    attempts = cache.incr(limit_key)
    if attempts > 5:
        return False
    key = f"can_{purpose}:{target}"
    result = cache.get(key)
    if result:
        cache.delete(key)
        return True
    return False
