"""
Audit routes.
"""

from django.urls import path

from apps.audit.views import AuditLogListView

urlpatterns = [
    path("", AuditLogListView.as_view(), name="audit-logs"),
]
