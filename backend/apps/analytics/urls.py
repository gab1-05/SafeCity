"""
Analytics routes: /api/v1/analytics/
"""

from django.urls import path

from apps.analytics.views import (
    AnalyticsBreakdownView,
    AnalyticsExportView,
    AnalyticsSummaryView,
    AnalyticsTrendView,
)

urlpatterns = [
    path("summary/", AnalyticsSummaryView.as_view(), name="analytics-summary"),
    path("trends/", AnalyticsTrendView.as_view(), name="analytics-trends"),
    path(
        "by-category/",
        AnalyticsBreakdownView.as_view(),
        {"dimension": "category"},
        name="analytics-by-category",
    ),
    path(
        "by-ward/",
        AnalyticsBreakdownView.as_view(),
        {"dimension": "ward"},
        name="analytics-by-ward",
    ),
    path(
        "by-department/",
        AnalyticsBreakdownView.as_view(),
        {"dimension": "department"},
        name="analytics-by-department",
    ),
    path(
        "by-status/",
        AnalyticsBreakdownView.as_view(),
        {"dimension": "status"},
        name="analytics-by-status",
    ),
    path(
        "by-severity/",
        AnalyticsBreakdownView.as_view(),
        {"dimension": "severity"},
        name="analytics-by-severity",
    ),
    path("export.csv/", AnalyticsExportView.as_view(), name="analytics-export"),
]
