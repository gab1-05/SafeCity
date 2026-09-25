"""Throwaway helper: measure query counts for list endpoints (delete after use)."""

from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.accounts.models import User


def measure(path, user_email=None):
    c = APIClient()
    if user_email:
        user = User.objects.filter(email=user_email).first()
        if user is None:
            print(f"{path} -> SKIP (no {user_email})")
            return
        c.force_authenticate(user=user)
    with CaptureQueriesContext(connection) as ctx:
        r = c.get(path, HTTP_HOST="localhost")
    print(f"{path} -> {r.status_code} | queries: {len(ctx.captured_queries)}")


print("── baseline measurements ──")
measure("/api/v1/departments/")
measure("/api/v1/categories/")
measure("/api/v1/admin/overview/", "admin@safecity.local")
