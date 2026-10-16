"""
Management commands: demo seeders, announcements seeder, role sync.
"""

import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command

from apps.accounts.models import Department, User, UserRole
from apps.announcements.management.commands.seed_announcements import SAMPLE_ANNOUNCEMENTS
from apps.announcements.models import Announcement
from apps.core.models import SLAConfiguration, Ward, Zone
from apps.incidents.models import Incident, IncidentCategory

pytestmark = pytest.mark.django_db


def test_seed_demo_data_minimal_then_full():
    call_command("seed_demo_data", "--minimal")
    assert Department.objects.count() == 8
    assert User.objects.filter(email="admin@safecity.local", role=UserRole.SUPERUSER).exists()
    assert Zone.objects.count() == 5
    assert Ward.objects.count() == 25
    assert IncidentCategory.objects.count() == 17
    assert SLAConfiguration.objects.count() == 4
    assert Incident.objects.count() == 0  # minimal skips incidents

    users_before = User.objects.count()
    call_command("seed_demo_data", "--minimal")  # idempotent rerun
    assert User.objects.count() == users_before
    assert Department.objects.count() == 8

    call_command("seed_demo_data")
    incidents = Incident.objects.count()
    assert incidents > 0
    assert Announcement.objects.filter(is_published=True).exists()

    call_command("seed_demo_data")  # incidents skipped on rerun
    assert Incident.objects.count() == incidents


def test_seed_demo_data_repairs_stale_role():
    User.objects.create_user(
        email="admin@safecity.local", password="StalePass123!", role=UserRole.CITIZEN
    )
    call_command("seed_demo_data", "--minimal")
    user = User.objects.get(email="admin@safecity.local")
    assert user.role == UserRole.SUPERUSER


def test_seed_announcements_without_admin_is_noop():
    call_command("seed_announcements")
    assert Announcement.objects.count() == 0


def test_seed_announcements_creates_idempotent_and_clears(admin):
    call_command("seed_announcements")
    assert Announcement.objects.count() == len(SAMPLE_ANNOUNCEMENTS)

    call_command("seed_announcements")  # rerun in the same process must work
    assert Announcement.objects.count() == len(SAMPLE_ANNOUNCEMENTS)

    call_command("seed_announcements", "--clear")
    assert Announcement.objects.count() == len(SAMPLE_ANNOUNCEMENTS)


def test_sync_roles_command_creates_groups():
    call_command("sync_roles")
    assert Group.objects.count() >= 1
