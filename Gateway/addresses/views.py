from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from .serializers import (
    AddUserAddressesSerializer,
    UpdateUserAddressesSerializer,
    DisplayUserAddressesSerializer,
    AddressInputMethod,
)
from django.db import IntegrityError, transaction
from .models import UserAddresses
from .utils.map import reverse_geocode, MapIrError
from django.conf import settings


class UserAddressView(APIView):
    @swagger_auto_schema(security=[{"Bearer": []}])
    def get(self, request, address_id=None):
        user = request.user
        if address_id:
            address = UserAddresses.objects.filter(user=user, id=address_id).first()
            if address is None:
                return Response(
                    {"detail": "address not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            serializer = DisplayUserAddressesSerializer(address)

        else:
            addresses = UserAddresses.objects.filter(user=user)
            if not addresses.exists():
                return Response(
                    {"detail": "no addresses"},
                    status=status.HTTP_200_OK,
                )
            serializer = DisplayUserAddressesSerializer(addresses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(security=[{"Bearer": []}])
    def post(self, request):
        user = request.user
        serializer = AddUserAddressesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        input_method = data["input_method"]  # type: ignore
        latitude = data.get("latitude")  # type: ignore
        longitude = data.get("longitude")  # type: ignore

        if input_method == AddressInputMethod.MAP:
            try:
                result = reverse_geocode(latitude, longitude)
                country = result.get("country")
                if country != "ایران":
                    return Response(
                        {"detail": "address must be in iran country"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                province = result.get("province")
                city = result.get("city")
                street = result.get("street")
                alley = result.get("alley")
                if not province or not city or not street:
                    raise MapIrError("reverse geocoding returned incomplete address")
            except MapIrError:
                return Response(
                    {"detail": "map service unavailable"},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
        else:
            province = data.get("province")  # type: ignore
            city = data.get("city")  # type: ignore
            street = data.get("street")  # type: ignore
            alley = data.get("alley")  # type: ignore

        try:
            with transaction.atomic():
                type(user).all_objects.select_for_update().get(pk=user.pk)  # type: ignore
                address_count = len(
                    list(
                        UserAddresses.objects.select_for_update()
                        .filter(user=user)
                        .values_list("id", flat=True)
                    )
                )
                if address_count >= settings.USER_MAX_ADDRESSES:
                    return Response(
                        {"detail": "you can't add addresses anymore"},
                        status=status.HTTP_403_FORBIDDEN,
                    )

                address = UserAddresses(
                    user=user,
                    is_default=address_count == 0,
                    latitude=latitude,
                    longitude=longitude,
                    title=data.get("title"),  # type: ignore
                    province=province,
                    city=city,
                    street=street,
                    alley=alley,
                    plaque=data["plaque"],  # type: ignore
                    unit=data.get("unit"),  # type: ignore
                    postal_code=data["postal_code"],  # type: ignore
                )
                address.save()
        except IntegrityError:
            return Response(
                {"detail": "could not create address"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "detail": "address added successfully",
                "input_method": input_method,
            },
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(security=[{"Bearer": []}])
    def put(self, request, address_id):
        user = request.user
        address = UserAddresses.objects.filter(user=user, id=address_id).first()
        if address is None:
            return Response(
                {"detail": "address not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = UpdateUserAddressesSerializer(
            address, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        is_default = data.get("is_default")  # type: ignore
        try:
            with transaction.atomic():
                if is_default is True:
                    UserAddresses.objects.select_for_update().filter(user=user).exclude(
                        id=address.id
                    ).update(is_default=False)
                serializer.save()
        except IntegrityError:
            return Response(
                {"detail": "could not update default address"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"detail": "address updated successfully"},
            status=status.HTTP_200_OK,
        )

    @swagger_auto_schema(security=[{"Bearer": []}])
    def delete(self, request, address_id):
        user = request.user
        address = UserAddresses.objects.filter(user=user, id=address_id).first()
        if address is None:
            return Response(
                {"detail": "address not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            was_default = address.is_default
            address.delete()
            if was_default:
                replacement = (
                    UserAddresses.objects.select_for_update()
                    .filter(user=user)
                    .order_by("id")
                    .first()
                )
                if replacement is not None:
                    replacement.is_default = True
                    replacement.save(update_fields=["is_default"])
        return Response(status=status.HTTP_204_NO_CONTENT)
