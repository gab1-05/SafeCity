"""
Management command to seed sample announcements.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.announcements.models import Announcement

SAMPLE_ANNOUNCEMENTS = [
    {
        "title": "Monsoon response: report waterlogging early",
        "body": "Use the map pin and attach a photo when it is safe. Drainage and disaster teams are prioritising high-risk subway, school and hospital routes this week.",
        "audience": "public",
        "is_pinned": True,
        "is_published": True,
        "days_ago": 0,
    },
    {
        "title": "Road repair blitz in central wards",
        "body": "Pothole reports verified before Friday evening will be batched into weekend repair routes. Reopen your report if the patch fails after rain.",
        "audience": "public",
        "is_pinned": False,
        "is_published": True,
        "days_ago": 1,
    },
    {
        "title": "Scheduled water maintenance — Ward 12 & 15",
        "body": "Water supply will be interrupted from 10 PM to 6 AM on 25th Sep for pipeline replacement. Please store water in advance. Emergency tankers available on request.",
        "audience": "citizens",
        "is_pinned": True,
        "is_published": True,
        "days_ago": 2,
    },
    {
        "title": "New waste segregation guidelines effective Oct 1",
        "body": "All households must separate wet, dry, and hazardous waste. Collection schedule changes: wet waste daily, dry waste Mon/Thu, hazardous first Saturday monthly. Download the guide from the portal.",
        "audience": "public",
        "is_pinned": False,
        "is_published": True,
        "days_ago": 3,
    },
    {
        "title": "Staff training: new incident triage protocol",
        "body": "All department staff must complete the updated triage training module by 30th Sep. The new protocol introduces severity-based auto-routing and SLA escalation timers. Access via the learning portal.",
        "audience": "staff",
        "is_pinned": True,
        "is_published": True,
        "days_ago": 0,
    },
    {
        "title": "Emergency contact numbers updated",
        "body": "Fire: 101 | Police: 100 | Ambulance: 108 | Disaster Control: 1916 | Water Emergency: 1916 | Electricity: 1912. Save these numbers. For non-emergencies, use the SafeCity app.",
        "audience": "public",
        "is_pinned": False,
        "is_published": True,
        "days_ago": 5,
    },
    {
        "title": "Community cleanup drive — this Saturday",
        "body": "Join volunteers at Dadar Beach, 7 AM onwards. Gloves, bags, and refreshments provided. Students earn community service hours. Register via the app or walk in.",
        "audience": "citizens",
        "is_pinned": False,
        "is_published": True,
        "days_ago": 7,
    },
    {
        "title": "Draft: Proposed parking policy changes",
        "body": "The department is reviewing residential parking permits and commercial loading zones. Feedback invited until 15th Oct. View the draft policy and submit comments on the portal.",
        "audience": "staff",
        "is_pinned": False,
        "is_published": False,
        "days_ago": 10,
    },
]


class Command(BaseCommand):
    help = "Seed sample announcements for demo/development"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Delete existing announcements first")

    def handle(self, *args, **options):
        if options["clear"]:
            Announcement.objects.all().delete()
            self.stdout.write(self.style.WARNING("Cleared existing announcements"))

        admin = User.objects.filter(role__in=[UserRole.CITY_ADMIN, UserRole.SUPERUSER], is_active=True).first()
        if not admin:
            self.stdout.write(self.style.ERROR("No admin/superuser found. Create one first."))
            return

        created = 0
        for ann_data in SAMPLE_ANNOUNCEMENTS:
            days = ann_data.pop("days_ago")
            published_at = timezone.now() - timedelta(days=days)

            ann, was_created = Announcement.objects.get_or_create(
                title=ann_data["title"],
                defaults={
                    **ann_data,
                    "published_at": published_at if ann_data["is_published"] else None,
                    "published_by": admin if ann_data["is_published"] else None,
                }
            )
            if was_created:
                created += 1
                self.stdout.write(f"Created: {ann.title}")
            else:
                self.stdout.write(f"Exists: {ann.title}")

        self.stdout.write(self.style.SUCCESS(f"Done. Created {created} new announcements."))
