import uuid
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from core.models import SoftDeleteManager, SoftDeleteModel
from accounts.utils.deletion import schedule_user_deleted_effects


class UserDeletionBackup(models.Model):
    user = models.OneToOneField(
        "accounts.CustomUser",
        on_delete=models.CASCADE,
        related_name="deletion_backup",
    )
    email = models.EmailField()
    phone = models.CharField(max_length=50)
    deleted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Backup for {self.user_id}"  # type: ignore


class UserManager(SoftDeleteManager, BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, phone, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        if not phone:
            raise ValueError("Phone is required")
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            phone=phone,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")
        return self.create_user(email, phone, password, **extra_fields)


class CustomUser(AbstractUser, SoftDeleteModel):
    email = models.EmailField(unique=True)
    phone = models.CharField(unique=True, max_length=16, db_index=True)

    image = models.ImageField(
        upload_to="users/avatars/",
        null=True,
        blank=True,
    )
    is_seller = models.BooleanField(default=False)
    tokens_invalid_before = models.DateTimeField(null=True, blank=True)
    username = None
    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["email", "first_name", "last_name"]
    objects = UserManager()  # type: ignore

    def backup_identity(self):
        UserDeletionBackup.objects.update_or_create(
            user=self,
            defaults={"email": self.email, "phone": self.phone},
        )

    def mark_deleted(self):
        unique_suffix = uuid.uuid4().hex
        self.email = f"deleted__{unique_suffix}@deleted.local"
        self.phone = f"deleted__{unique_suffix}"
        self.is_deleted = True
        self.image = None
        self.tokens_invalid_before = timezone.now()

    def get_restore_value(self, field_name, original_value, replacement):
        user_model = type(self)
        conflict = (
            user_model.objects.filter(**{field_name: original_value})
            .exclude(id=self.id)  # type: ignore
            .exists()
        )
        if not conflict:
            return original_value

        if not replacement:
            raise ValidationError(
                f"Original {field_name} is already in use. Provide a new {field_name}."
            )
        replacement_conflict = user_model.objects.filter(
            **{field_name: replacement}
        ).exists()
        if replacement_conflict:
            raise ValidationError(f"New {field_name} is already in use.")
        return replacement

    @transaction.atomic
    def delete(self, using=None, keep_parents=False):
        avatar_name = self.image.name if self.image else None
        email_to_notify = self.email

        self.backup_identity()
        self.mark_deleted()
        self.save(
            update_fields=[
                "email",
                "phone",
                "is_deleted",
                "image",
                "tokens_invalid_before",
            ]
        )
        schedule_user_deleted_effects(self, email_to_notify, avatar_name)

    @transaction.atomic
    def restore(self, new_email=None, new_phone=None):
        if not self.is_deleted:
            raise ValidationError("User is not deleted.")
        try:
            backup = self.deletion_backup  # type: ignore
        except UserDeletionBackup.DoesNotExist:
            raise ValidationError("No backup exists for this user.")

        target_email = self.get_restore_value("email", backup.email, new_email)
        target_phone = self.get_restore_value("phone", backup.phone, new_phone)
        self.email = target_email
        self.phone = target_phone
        self.is_deleted = False
        self.save(update_fields=["email", "phone", "is_deleted"])
        backup.delete()

    def __str__(self):
        return f"{self.get_full_name().strip()} - {self.phone}"
