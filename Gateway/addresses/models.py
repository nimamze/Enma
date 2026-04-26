from django.conf import settings
from core.models import BaseModel
from django.db import models


class UserAddresses(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses"
    )
    is_default = models.BooleanField(default=False)
    latitude = models.FloatField()
    longitude = models.FloatField()
    title = models.CharField(max_length=50)
    province = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    street = models.CharField(max_length=255)
    alley = models.CharField(max_length=255, blank=True, null=True)
    plaque = models.CharField(max_length=20)
    unit = models.CharField(max_length=20, blank=True, null=True)

    @property
    def full_address(self):
        parts = [
            self.province,
            self.city,
            self.street,
        ]
        if self.alley:
            parts.append(self.alley)
        parts.append(self.plaque)
        if self.unit:
            parts.append(self.unit)
        return " - ".join(parts)

    def __str__(self):
        return (
            f"{self.user.get_full_name()} — {self.title} | {self.city}, {self.street}"
        )
