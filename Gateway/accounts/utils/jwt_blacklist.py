from django.core.cache import cache
import time
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)


def blacklist_access_token(jti: str, exp: int):
    ttl = exp - int(time.time())
    if ttl > 0:
        cache.set(f"access_blacklist:{jti}", "1", timeout=ttl)


def is_access_token_blacklisted(jti: str):
    return cache.get(f"access_blacklist:{jti}") is not None


def blacklist_user_refresh_tokens(user):
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)
