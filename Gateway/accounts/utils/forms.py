from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from accounts.models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ("phone", "email", "first_name", "last_name")


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ("phone", "email", "first_name", "last_name", "image", "is_seller")
