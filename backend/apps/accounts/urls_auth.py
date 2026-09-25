"""
Authentication API routes: /api/v1/auth/...
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from apps.accounts.views_auth import (
    ChangePasswordView,
    GoogleOAuthView,
    LoginThrottledView,
    LogoutView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    SessionDeleteView,
    SessionListView,
)
from apps.accounts.views_2fa import (
    TwoFactorDisableView,
    TwoFactorRegenerateRecoveryCodesView,
    TwoFactorSetupView,
    TwoFactorVerifyLoginView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("token/", LoginThrottledView.as_view(), name="auth-token"),
    path("token/2fa/", TwoFactorVerifyLoginView.as_view(), name="auth-token-2fa"),
    path("oauth/google/", GoogleOAuthView.as_view(), name="auth-oauth-google"),
    path("token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="auth-token-verify"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("password/reset/", PasswordResetRequestView.as_view(), name="auth-password-reset"),
    path(
        "password/reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
    path("password/change/", ChangePasswordView.as_view(), name="auth-password-change"),
    path("sessions/", SessionListView.as_view(), name="auth-sessions"),
    path("sessions/<uuid:pk>/", SessionDeleteView.as_view(), name="auth-session-delete"),
    # 2FA
    path("2fa/setup/", TwoFactorSetupView.as_view(), name="auth-2fa-setup"),
    path("2fa/disable/", TwoFactorDisableView.as_view(), name="auth-2fa-disable"),
    path(
        "2fa/recovery/regenerate/",
        TwoFactorRegenerateRecoveryCodesView.as_view(),
        name="auth-2fa-recovery-regenerate",
    ),
]