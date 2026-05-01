from django.core.cache import cache
from rest_framework import serializers


def atomic_rate_limit(key: str, ttl: int, max_attempts: int):
    cache.add(key, 0, timeout=ttl)
    attempts = cache.incr(key)
    if attempts > max_attempts:
        raise serializers.ValidationError("rate limit exceeded")
