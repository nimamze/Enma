from datetime import datetime, timezone as dt_timezone
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from accounts.utils.jwt_blacklist import is_access_token_blacklisted

User = get_user_model()


def validate_token_user(token, exception_class):
    user_id = token.get("user_id")
    if not user_id:
        raise exception_class("Token contained no recognizable user identification")

    user = User.all_objects.filter(pk=user_id).first()  # type: ignore
    if user is None or user.is_deleted:
        raise exception_class("User account is not active.")

    tokens_invalid_before = getattr(user, "tokens_invalid_before", None)
    token_iat = token.get("iat")
    if tokens_invalid_before and token_iat:
        issued_at = datetime.fromtimestamp(token_iat, tz=dt_timezone.utc)
        if issued_at <= tokens_invalid_before.astimezone(dt_timezone.utc):
            raise exception_class("Token has been invalidated.")

    return user


class RedisBlacklistJWTAuthentication(JWTAuthentication):
    def get_validated_token(self, raw_token):
        token = super().get_validated_token(raw_token)
        jti = token.get("jti")
        if jti and is_access_token_blacklisted(jti):
            raise AuthenticationFailed("Token has been blacklisted (user logged out).")
        return token

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        validate_token_user(validated_token, AuthenticationFailed)
        return user
