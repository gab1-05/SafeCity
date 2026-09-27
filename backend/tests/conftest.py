"""
Shared pytest fixtures: users for every role, departments, categories, wards.
"""

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Department, User, UserRole
from apps.core.models import SLAConfiguration, Ward, Zone
from apps.incidents.models import IncidentCategory


@pytest.fixture
def client():
    """DRF API client (overrides Django's default)."""
    return APIClient()


@pytest.fixture(autouse=True)
def _clear_cache():
    """Response caching (analytics summary, public incident list) uses the
    shared LocMem cache in tests — clear it so no test reads another's rows."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def db(db):  # noqa: F811 — pytest-django db fixture
    return None


@pytest.fixture
def department(db):
    return Department.objects.create(name="Roads & Infrastructure", code="roads")


@pytest.fixture
def water_department(db):
    return Department.objects.create(name="Water Department", code="water")


@pytest.fixture
def ward(db):
    zone = Zone.objects.create(name="Zone 1", code="z1")
    return Ward.objects.create(
        name="Zone 1 Ward 1", code="z1-w1", zone=zone, latitude=19.076, longitude=72.8777
    )


@pytest.fixture
def category(db, department):
    return IncidentCategory.objects.create(
        name="Road damage", slug="road-damage", default_department=department
    )


@pytest.fixture
def water_category(db, water_department):
    return IncidentCategory.objects.create(
        name="Water leakage", slug="water-leakage", default_department=water_department
    )


@pytest.fixture
def sla_rules(db):
    for severity, hours in [("low", 120), ("medium", 72), ("high", 24), ("critical", 6)]:
        SLAConfiguration.objects.create(severity=severity, resolution_hours=hours)


def make_user(email, role, password="Testpass123!", **kwargs):
    return User.objects.create_user(
        email=email,
        password=password,
        role=role,
        first_name=kwargs.pop("first_name", "Test"),
        last_name=kwargs.pop("last_name", "User"),
        **kwargs,
    )


@pytest.fixture
def citizen(db):
    return make_user("citizen@test.local", UserRole.CITIZEN)


@pytest.fixture
def staff(db, department):
    return make_user("staff@test.local", UserRole.DEPARTMENT_STAFF, department=department)


@pytest.fixture
def other_dept_staff(db, water_department):
    return make_user(
        "otherstaff@test.local", UserRole.DEPARTMENT_STAFF, department=water_department
    )


@pytest.fixture
def responder(db):
    return make_user("responder@test.local", UserRole.EMERGENCY_RESPONDER)


@pytest.fixture
def volunteer(db):
    return make_user("volunteer@test.local", UserRole.VOLUNTEER)


@pytest.fixture
def admin(db):
    return make_user("admin@test.local", UserRole.CITY_ADMIN)


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser("super@test.local", "Superpass123!")


@pytest.fixture
def incident_factory(db, category, ward):
    """Factory: create a submitted incident with defaults."""

    def _make(reporter=None, **overrides):
        from apps.incidents.models import Incident

        defaults = {
            "title": "Pothole near the bus stop",
            "description": "A large pothole has opened up and damages vehicles daily.",
            "category": category,
            "severity": "high",
            "status": "submitted",
            "reporter": reporter,
            "ward": ward,
            "latitude": 19.076,
            "longitude": 72.8777,
            "address_public": "Near the bus stop",
            "department": category.default_department,
        }
        defaults.update(overrides)
        incident = Incident(**defaults)
        incident.submitted_at = timezone.now()
        incident.save()
        return incident

    return _make


@pytest.fixture
def incident(incident_factory, citizen):
    return incident_factory(reporter=citizen)
