"""
Announcement serializers.
"""

from rest_framework import serializers

from apps.announcements.models import Announcement


class AnnouncementSerializer(serializers.ModelSerializer):
    published_by_email = serializers.CharField(
        source="published_by.email", read_only=True, default=None
    )

    class Meta:
        model = Announcement
        fields = [
            "id",
            "title",
            "body",
            "audience",
            "is_pinned",
            "is_published",
            "published_at",
            "published_by_email",
            "created_at",
        ]
        read_only_fields = ["is_published", "published_at", "published_by_email", "created_at"]
