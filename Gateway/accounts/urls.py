from django.urls import path
from .views import (
    SignUpView,
    LogOut,
    ProfileView,
    SendOtpView,
    VerifyOtpView,
    SellerView,
    PhoneChangeView,
    PasswordChangeView,
    PasswordForgetResetView,
)

urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("logout/", LogOut.as_view(), name="logout"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("otp/send/", SendOtpView.as_view(), name="otp_send"),
    path("otp/verify/", VerifyOtpView.as_view(), name="otp_verify"),
    path("password-change/", PasswordChangeView.as_view(), name="password_change"),
    path("password-reset/", PasswordForgetResetView.as_view(), name="password_reset"),
    path("phone-change/", PhoneChangeView.as_view(), name="phone_change"),
    path("seller/", SellerView.as_view(), name="seller"),
]
