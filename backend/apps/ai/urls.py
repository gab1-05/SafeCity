"""
AI routes: /api/v1/ai/
"""

from django.urls import path

from apps.ai.views import (
    AIDecisionView,
    AIDuplicateCheckView,
    AISuggestView,
)

urlpatterns = [
    path("incidents/<uuid:incident_id>/suggest/", AISuggestView.as_view(), name="ai-suggest"),
    path(
        "recommendations/<uuid:recommendation_id>/decide/",
        AIDecisionView.as_view(),
        name="ai-decide",
    ),
    path("duplicates/", AIDuplicateCheckView.as_view(), name="ai-duplicates"),
]
