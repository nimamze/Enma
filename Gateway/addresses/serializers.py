from rest_framework import serializers
from django.db import models
from .models import UserAddresses


class AddressInputMethod(models.TextChoices):
    MAP = "map", "map"
    MANUAL = "manual", "manual"


MANUAL_ADDRESS_FIELDS = ("province", "city", "street")


class AddUserAddressesSerializer(serializers.ModelSerializer):
    input_method = serializers.ChoiceField(choices=AddressInputMethod.choices)
    latitude = serializers.FloatField(write_only=True, required=False, allow_null=True)
    longitude = serializers.FloatField(write_only=True, required=False, allow_null=True)
    province = serializers.CharField(required=False)
    city = serializers.CharField(required=False)
    street = serializers.CharField(required=False)
    alley = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = UserAddresses
        fields = [
            "input_method",
            "latitude",
            "longitude",
            "title",
            "province",
            "city",
            "street",
            "alley",
            "plaque",
            "unit",
            "postal_code",
        ]

    def validate(self, data):
        input_method = data["input_method"]
        if input_method == AddressInputMethod.MAP:
            missing_fields = [
                field for field in ("latitude", "longitude") if data.get(field) is None
            ]
        else:
            missing_fields = [
                field for field in MANUAL_ADDRESS_FIELDS if not data.get(field)
            ]
        if missing_fields:
            raise serializers.ValidationError(
                {
                    "detail": f"{input_method} address fields are incomplete",
                    "required_fields": missing_fields,
                }
            )
        return data


class UpdateUserAddressesSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAddresses
        fields = [
            "is_default",
            "title",
            "street",
            "alley",
            "plaque",
            "unit",
            "postal_code",
        ]


class DisplayUserAddressesSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAddresses
        fields = [
            "id",
            "is_default",
            "title",
            "province",
            "city",
            "street",
            "alley",
            "plaque",
            "unit",
            "postal_code",
        ]
