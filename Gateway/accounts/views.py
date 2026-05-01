from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema
from .serializers import (
    SignUpSerializer,
    UserProfileSerializer,
    UserUpdateSerializer,
    SendOtpSerializer,
    VerifyOtpSerializer,
    PasswordChangeSerializer,
    PasswordForgetResetSerializer,
    PhoneChangeSerializer,
    OtpPurpose,
    OtpSendWay,
)
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from django.utils import timezone
from .utils.jwt_blacklist import blacklist_access_token
from django.core.cache import cache
from core.utils.tasks import enqueue_task, send_email_task, send_sms_task
from django.conf import settings
from rest_framework import serializers
import secrets
from django.db import IntegrityError, transaction
from accounts.utils.rate_limit import atomic_rate_limit
from accounts.utils.otp_consume import consume_otp_authorization
from accounts.utils.jwt_blacklist import blacklist_user_refresh_tokens


def build_otp_key(purpose, target):
    return f"{purpose}_otp_send:{target}"


class SendOtpView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user = request.user
        serializer = SendOtpSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if user.is_authenticated:
            if data["send_way"] == OtpSendWay.SMS:  # type: ignore
                data["user_phone"] = user.phone  # type: ignore
            else:
                data["user_email"] = user.email  # type: ignore
        phone = data.get("user_phone")  # type: ignore
        email = data.get("user_email")  # type: ignore
        purpose = data["purpose"]  # type: ignore
        if phone:
            atomic_rate_limit(
                key=f"otp_send_limit:{purpose}:{phone}",
                ttl=settings.OTP_RATE_LIMIT_TTL,
                max_attempts=settings.RATE_LIMIT_OTP_DAILY,
            )
        if email and not phone:
            atomic_rate_limit(
                key=f"otp_send_email_limit:{purpose}:{email}",
                ttl=settings.OTP_RATE_LIMIT_TTL,
                max_attempts=settings.RATE_LIMIT_OTP_DAILY,
            )
        target = phone if phone else email
        otp_key = build_otp_key(purpose, target)
        otp = cache.get(otp_key)
        if otp is None:
            otp = secrets.randbelow(900000) + 100000
            cache.set(otp_key, otp, settings.OTP_TTL)
        if data["send_way"] == OtpSendWay.EMAIL:  # type: ignore
            enqueue_task(send_email_task, email, f"your code is {otp}")  # type: ignore
        else:
            enqueue_task(send_sms_task, phone, f"your code is {otp}")  # type: ignore
        return Response({"detail": "OTP sent"}, status=status.HTTP_200_OK)


class VerifyOtpView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyOtpSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if request.user.is_authenticated:
            if data["send_way"] == OtpSendWay.SMS:  # type: ignore
                data["user_phone"] = request.user.phone  # type: ignore
            else:
                data["user_email"] = request.user.email  # type: ignore
        phone = data.get("user_phone")  # type: ignore
        email = data.get("user_email")  # type: ignore
        otp = data["validation_otp"]  # type: ignore
        purpose = data["purpose"]  # type: ignore
        if phone:
            atomic_rate_limit(
                key=f"otp_verify_limit:{purpose}:{phone}",
                ttl=settings.OTP_RATE_LIMIT_TTL,
                max_attempts=settings.RATE_LIMIT_OTP_DAILY,
            )
            otp_key = build_otp_key(purpose, phone)
        else:
            atomic_rate_limit(
                key=f"otp_verify_email_limit:{purpose}:{email}",
                ttl=settings.OTP_RATE_LIMIT_TTL,
                max_attempts=settings.RATE_LIMIT_OTP_DAILY,
            )
            otp_key = build_otp_key(purpose, email)
        sent = cache.get(otp_key)
        if sent is None or str(sent) != str(otp):
            raise serializers.ValidationError("invalid or expired otp")
        cache.delete(otp_key)
        can_key_targets = {phone if phone else email}
        if request.user.is_authenticated:  # type: ignore
            can_key_targets.add(request.user.phone)  # type: ignore
            if request.user.email:  # type: ignore
                can_key_targets.add(request.user.email)  # type: ignore
        ttl = (
            settings.OTP_SIGNUP_TTL
            if purpose == OtpPurpose.SIGN_UP
            else settings.OTP_AUTHORIZATION_TTL
        )
        for can_key_target in can_key_targets:
            if can_key_target:
                cache.set(f"can_{purpose}:{can_key_target}", True, ttl)
        return Response({"detail": "OTP verified"}, status=status.HTTP_200_OK)


def logOut(request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return False
    access_token_str = auth_header.split(" ")[1]
    refresh_token_str = request.data.get("refresh")
    try:
        access_token = AccessToken(access_token_str)
        jti = access_token["jti"]
        exp = access_token["exp"]
        blacklist_access_token(jti, exp)  # type: ignore
        if refresh_token_str:
            refresh_token = RefreshToken(refresh_token_str)
            refresh_token.blacklist()
        return True
    except Exception:
        return False


class SignUpView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_phone = serializer.validated_data["phone"]  # type: ignore
        if consume_otp_authorization(target=user_phone, purpose=OtpPurpose.SIGN_UP):
            user = serializer.save()
            output = UserProfileSerializer(user)
            return Response({"detail": output.data}, status=status.HTTP_201_CREATED)
        else:
            return Response(
                {"detail": "otp authorization failed"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class LogOut(APIView):
    @swagger_auto_schema(security=[{"Bearer": []}])
    def post(self, request):
        result = logOut(request)
        if result:
            return Response({"detail": "Logged out successfully."})
        else:
            return Response(
                {"detail": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST
            )


class ProfileView(APIView):
    @swagger_auto_schema(security=[{"Bearer": []}])
    def get(self, request):
        user = request.user
        serializer = UserProfileSerializer(user)
        return Response({"detail": serializer.data}, status=status.HTTP_200_OK)

    @swagger_auto_schema(security=[{"Bearer": []}])
    def put(self, request):
        user = request.user
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        output = UserUpdateSerializer(user)
        return Response({"detail": output.data}, status=status.HTTP_200_OK)

    @swagger_auto_schema(security=[{"Bearer": []}])
    def delete(self, request):
        user = request.user
        user.delete()
        logOut(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SellerView(APIView):
    @swagger_auto_schema(security=[{"Bearer": []}])
    def get(self, request):
        user = request.user
        if user.is_seller:
            message = "you are a seller"
        else:
            message = "you are not a seller"
        return Response({"detail": message}, status=status.HTTP_200_OK)

    @swagger_auto_schema(security=[{"Bearer": []}])
    def post(self, request):
        user = request.user
        if user.is_seller:
            message = "you are already a seller"
        else:
            user_phone = user.phone
            if consume_otp_authorization(
                target=user_phone,
                purpose=OtpPurpose.BECOME_SELLER,
            ):
                user.is_seller = True
                user.save()
                message = "you become a seller"
            else:
                return Response(
                    {"detail": "otp authorization failed"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return Response({"detail": message}, status=status.HTTP_200_OK)

    @swagger_auto_schema(security=[{"Bearer": []}])
    def delete(self, request):
        user = request.user
        if not user.is_seller:
            message = "you are not a seller"
        else:
            user.is_seller = False
            user.save()
            message = "you are not a seller any more"
        return Response({"detail": message}, status=status.HTTP_200_OK)


class PhoneChangeView(APIView):
    @swagger_auto_schema(security=[{"Bearer": []}])
    def post(self, request):
        user = request.user
        phone = user.phone
        atomic_rate_limit(
            key=f"phone_change_limit:{phone}",
            ttl=settings.RATE_LIMIT_PHONE_CHANGE,
            max_attempts=1,
        )
        if not consume_otp_authorization(
            target=phone, purpose=OtpPurpose.PHONE_CHANGE
        ):
            return Response(
                {"detail": "otp authorization failed"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = PhoneChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data["previous_phone"] != phone:  # type: ignore
            return Response(
                {"detail": "previous phone doesn't match"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            with transaction.atomic():
                user.phone = data["new_phone"]  # type: ignore
                user.save()
        except IntegrityError:
            return Response(
                {"detail": "phone exists"}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response({"detail": "phone changed"}, status=status.HTTP_200_OK)


class PasswordChangeView(APIView):
    @swagger_auto_schema(security=[{"Bearer": []}])
    def post(self, request):
        user = request.user
        phone = user.phone
        atomic_rate_limit(
            key=f"password_change_limit:{phone}",
            ttl=settings.RATE_LIMIT_PASSWORD_CHANGE,
            max_attempts=1,
        )
        if not consume_otp_authorization(
            target=phone,
            purpose=OtpPurpose.PASSWORD_CHANGE,
        ):
            return Response(
                {"detail": "otp authorization failed"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_password = serializer.validated_data["new_password"]  # type: ignore
        with transaction.atomic():
            user.set_password(new_password)
            user.tokens_invalid_before = timezone.now()  # type: ignore
            user.save(update_fields=["password", "tokens_invalid_before"])
            transaction.on_commit(lambda: blacklist_user_refresh_tokens(user))
        return Response({"detail": "password changed"}, status=status.HTTP_200_OK)


class PasswordForgetResetView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordForgetResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        target = (
            data["user_phone"]  # type: ignore
            if data["send_way"] == OtpSendWay.SMS  # type: ignore
            else data["user_email"]  # type: ignore
        )
        atomic_rate_limit(
            key=f"password_reset_limit:{target}",
            ttl=settings.RATE_LIMIT_PASSWORD_RESET,
            max_attempts=1,
        )
        if not consume_otp_authorization(
            target=target,
            purpose=OtpPurpose.PASSWORD_FORGET,
        ):
            return Response(
                {"detail": "otp authorization failed"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = data["user"]  # type: ignore
        with transaction.atomic():
            user.set_password(data["new_password"])  # type: ignore
            user.tokens_invalid_before = timezone.now()  # type: ignore
            user.save(update_fields=["password", "tokens_invalid_before"])
            transaction.on_commit(lambda: blacklist_user_refresh_tokens(user))
        return Response(
            {"detail": "password reset successfully"},
            status=status.HTTP_200_OK,
        )
