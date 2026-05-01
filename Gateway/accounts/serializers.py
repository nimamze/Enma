from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import models
import phonenumbers
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class OtpSendWay(models.TextChoices):
    SMS = "sms", "sms"
    EMAIL = "email", "email"


class OtpPurpose(models.TextChoices):
    SIGN_UP = "sign_up", "sign_up"
    BECOME_SELLER = "become_seller", "become_seller"
    PHONE_CHANGE = "phone_change", "phone_change"
    PASSWORD_CHANGE = "password_change", "password_change"
    PASSWORD_FORGET = "password_forget", "password_forget"


def validate_iran_phone(phone):
    try:
        phone = phonenumbers.parse(phone, "IR")
        if not phonenumbers.is_valid_number(phone):
            raise serializers.ValidationError("Invalid Iranian phone number")
        if phonenumbers.region_code_for_number(phone) != "IR":
            raise serializers.ValidationError("Phone must belong to Iran")
        phone = phonenumbers.format_number(phone, phonenumbers.PhoneNumberFormat.E164)
        return phone
    except phonenumbers.NumberParseException:
        raise serializers.ValidationError("Invalid phone format")


def validate_confirmed_password(password, password_confirm):
    validate_password(password)
    if password != password_confirm:
        raise serializers.ValidationError(
            "password and password_confirm are not same as each other!"
        )


def validate_otp_target(
    data,
    request,
    phone_required_message,
    email_required_message,
):
    send_way = data["send_way"]
    purpose = data["purpose"]
    if purpose == OtpPurpose.SIGN_UP and send_way != OtpSendWay.SMS:
        raise serializers.ValidationError("sign up otp must be sent by sms")

    if request and request.user.is_authenticated:  # type: ignore
        return data

    if send_way == OtpSendWay.SMS:
        if not data.get("user_phone"):
            raise serializers.ValidationError(phone_required_message)
        data["user_phone"] = validate_iran_phone(data["user_phone"])
        return data

    if not data.get("user_email"):
        raise serializers.ValidationError(email_required_message)
    return data


class SignUpSerializer(serializers.ModelSerializer):
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            "phone",
            "email",
            "first_name",
            "last_name",
            "password",
            "password_confirm",
        ]
        extra_kwargs = {
            "password": {"write_only": True},
            "password_confirm": {"write_only": True},
        }

    def create(self, validated_data):
        password = validated_data.pop("password")
        validated_data.pop("password_confirm", None)
        return User.objects.create_user(password=password, **validated_data)

    def validate(self, data):
        validate_confirmed_password(data.get("password"), data.get("password_confirm"))
        data["phone"] = validate_iran_phone(data.get("phone"))
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "image", "phone", "email"]


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "image", "email"]


class BaseOtpSerializer(serializers.Serializer):
    user_email = serializers.EmailField(required=False, allow_blank=True)
    user_phone = serializers.CharField(required=False, allow_blank=True)
    send_way = serializers.ChoiceField(choices=OtpSendWay.choices)
    purpose = serializers.ChoiceField(choices=OtpPurpose.choices)


class SendOtpSerializer(BaseOtpSerializer):

    def validate(self, data):
        return validate_otp_target(
            data=data,
            request=self.context.get("request"),
            phone_required_message="Phone required for sms",
            email_required_message="Email required for email",
        )


class VerifyOtpSerializer(BaseOtpSerializer):
    validation_otp = serializers.CharField(max_length=6)

    def validate(self, data):
        return validate_otp_target(
            data=data,
            request=self.context.get("request"),
            phone_required_message="phone required for verify",
            email_required_message="email required for verify",
        )


class PasswordChangeSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, required=True)
    new_confirm_password = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        validate_confirmed_password(
            data.get("new_password"),
            data.get("new_confirm_password"),
        )
        return data


class PasswordForgetResetSerializer(PasswordChangeSerializer):
    user_email = serializers.EmailField(required=False, allow_blank=True)
    user_phone = serializers.CharField(required=False, allow_blank=True)
    send_way = serializers.ChoiceField(choices=OtpSendWay.choices)

    def validate(self, data):
        data = super().validate(data)
        send_way = data["send_way"]
        if send_way == OtpSendWay.SMS:
            if not data.get("user_phone"):
                raise serializers.ValidationError("phone required for password reset")
            data["user_phone"] = validate_iran_phone(data["user_phone"])
            lookup = {"phone": data["user_phone"]}
        else:
            if not data.get("user_email"):
                raise serializers.ValidationError("email required for password reset")
            lookup = {"email": data["user_email"]}
        try:
            data["user"] = User.objects.get(**lookup)
        except User.DoesNotExist:
            raise serializers.ValidationError("user not found")
        return data


class PhoneChangeSerializer(serializers.Serializer):
    previous_phone = serializers.CharField(max_length=16, required=True)
    new_phone = serializers.CharField(max_length=16, required=True)

    def validate(self, data):
        data["new_phone"] = validate_iran_phone(data.get("new_phone"))
        data["previous_phone"] = validate_iran_phone(data.get("previous_phone"))
        return data
