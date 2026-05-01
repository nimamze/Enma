from django.conf import settings
from core.models import BaseModel
from django.db import models


class UserAddresses(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses"
    )
    is_default = models.BooleanField(default=False)
    latitude = models.FloatField(db_index=True, null=True, blank=True)
    longitude = models.FloatField(db_index=True, null=True, blank=True)
    title = models.CharField(max_length=50, blank=True, null=True)
    province = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    street = models.CharField(max_length=255)
    alley = models.CharField(max_length=255, blank=True, null=True)
    plaque = models.CharField(max_length=20)
    unit = models.CharField(max_length=20, blank=True, null=True)
    postal_code = models.CharField(max_length=20)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default=True),
                name="unique_default_address_per_user",
            )
        ]

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
        parts.append(self.postal_code)
        return " - ".join(parts)

    def __str__(self):
        return f"{self.user.get_full_name()} | {self.province} - {self.city} - {self.street}"
