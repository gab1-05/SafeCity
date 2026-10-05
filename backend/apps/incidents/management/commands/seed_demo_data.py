"""
Seed demo data for local development and demos.

Creates clearly-fake users (documented in README), departments, categories,
zones/wards, incidents across statuses, comments, assignments, notifications,
announcements and SLA rules. Safe to re-run: idempotent on emails/codes.
"""

import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import Department, User, UserRole
from apps.announcements.models import Announcement
from apps.core.models import SLAConfiguration, Ward, Zone
from apps.incidents.models import (
    Incident,
    IncidentCategory,
    IncidentComment,
    IncidentStatus,
)

SEED_LAT, SEED_LNG = 19.0760, 72.8777  # Mumbai city center (illustrative)


class Command(BaseCommand):
    help = "Seed demo data for local development (fake credentials only)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--minimal",
            action="store_true",
            help="Seed reference data + users only (fast CI path); skips incidents and announcements.",
        )

    def handle(self, *args, **options):
        self.stdout.write("Seeding SafeCity demo data…")
        self._departments()
        self._users()
        self._zones_and_wards()
        self._categories()
        self._sla_rules()
        if options["minimal"]:
            self.stdout.write(self.style.SUCCESS("Minimal seed done (reference data + users)."))
            return
        self._incidents()
        self._announcements()
        self.stdout.write(self.style.SUCCESS("Demo data seeded."))

    # ── helpers ──────────────────────────────────────────────
    def _get_user(self, email, password, **fields):
        user, created = User.objects.get_or_create(email=email, defaults=fields)
        if created:
            user.set_password(password)
            user.save(update_fields=["password"])
        elif "role" in fields and user.role != fields["role"]:
            # Re-running the seeder must repair accounts seeded with a stale
            # role (citizen demo logins were once seeded as volunteers).
            user.role = fields["role"]
            user.save(update_fields=["role"])
        return user

    def _departments(self):
        self.depts = {}
        for name, code, emergency in [
            ("Roads & Infrastructure", "roads", False),
            ("Water Department", "water", False),
            ("Fire Services", "fire", True),
            ("Solid Waste Management", "swm", False),
            ("Electricity Department", "electricity", False),
            ("Health Services", "health", False),
            ("Law & Order", "law-order", True),
            ("Disaster Management", "disaster", True),
        ]:
            dept, _ = Department.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "is_emergency_department": emergency,
                    "contact_email": f"{code}@safecity.local",
                },
            )
            self.depts[code] = dept

    def _users(self):
        self.admin = self._get_user(
            "admin@safecity.local",
            "Admin@12345!",
            role=UserRole.SUPERUSER,
            first_name="Asha",
            last_name="Admin",
            is_staff=True,
            is_superuser=True,
        )
        self.staff = {}
        for code, email, name in [
            ("roads", "staff.roads@safecity.local", "Ravi Roadworks"),
            ("water", "staff.water@safecity.local", "Waman Waterworks"),
            ("fire", "staff.fire@safecity.local", "Farah Firestone"),
            ("swm", "staff.swm@safecity.local", "Sana Sweeper"),
            ("electricity", "staff.electricity@safecity.local", "Eshan Volt"),
        ]:
            self.staff[code] = self._get_user(
                email,
                "Staff@12345!",
                role=UserRole.DEPARTMENT_STAFF,
                first_name=name.split()[0],
                last_name=name.split()[-1],
                department=self.depts[code],
            )
        self.responder = self._get_user(
            "responder@safecity.local",
            "Responder@12345!",
            role=UserRole.EMERGENCY_RESPONDER,
            first_name="Rohit",
            last_name="Rescue",
            department=self.depts["disaster"],
        )
        self.volunteer = self._get_user(
            "volunteer@safecity.local",
            "Volunteer@12345!",
            role=UserRole.VOLUNTEER,
            first_name="Veena",
            last_name="Helper",
        )
        self.citizens = [
            self._get_user(
                f"citizen{i}@safecity.local",
                "Citizen@12345!",
                role=UserRole.CITIZEN,
                first_name=f"Citizen{i}",
                last_name="Test",
                phone=f"+91980000000{i}",
            )
            for i in range(1, 6)
        ]

    def _zones_and_wards(self):
        self.wards = []
        zone_defs = [
            ("North Zone", "north"),
            ("South Zone", "south"),
            ("East Zone", "east"),
            ("West Zone", "west"),
            ("Central Zone", "central"),
        ]
        for zname, zcode in zone_defs:
            zone, _ = Zone.objects.get_or_create(code=zcode, defaults={"name": zname})
            for widx in range(1, 6):
                ward, _ = Ward.objects.get_or_create(
                    code=f"{zcode}-w{widx}",
                    defaults={
                        "name": f"{zname} Ward {widx}",
                        "zone": zone,
                        "latitude": SEED_LAT + random.uniform(-0.08, 0.08),
                        "longitude": SEED_LNG + random.uniform(-0.08, 0.08),
                    },
                )
                self.wards.append(ward)

    def _categories(self):
        self.categories = {}
        cat_defs = [
            ("Road damage", "road-damage", "roads", False),
            ("Traffic accident", "traffic-accident", "law-order", True),
            ("Fire", "fire", "fire", True),
            ("Flooding or waterlogging", "flooding", "disaster", True),
            ("Garbage accumulation", "garbage-accumulation", "swm", False),
            ("Broken streetlight", "broken-streetlight", "electricity", False),
            ("Water leakage", "water-leakage", "water", False),
            ("Electrical hazard", "electrical-hazard", "electricity", True),
            ("Public safety threat", "public-safety-threat", "law-order", True),
            ("Medical emergency", "medical-emergency", "health", True),
            ("Missing person", "missing-person", "law-order", False),
            ("Illegal dumping", "illegal-dumping", "swm", False),
            ("Noise complaint", "noise-complaint", "law-order", False),
            ("Stray animal", "stray-animal", "health", False),
            ("Building damage", "building-damage", "roads", False),
            ("Sanitation", "sanitation", "health", False),
            ("Other", "other", None, False),
        ]
        for order, (name, slug, dept_code, emergency) in enumerate(cat_defs, start=1):
            cat, _ = IncidentCategory.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "slug": slug,
                    "default_department": self.depts.get(dept_code),
                    "is_emergency_category": emergency,
                    "display_order": order * 10,
                },
            )
            self.categories[slug] = cat

    def _sla_rules(self):
        for severity, response_h, resolution_h in [
            ("low", 48, 120),
            ("medium", 24, 72),
            ("high", 8, 24),
            ("critical", 1, 6),
        ]:
            SLAConfiguration.objects.get_or_create(
                category=None,
                severity=severity,
                defaults={"response_hours": response_h, "resolution_hours": resolution_h},
            )

    def _incidents(self):
        if Incident.objects.exists():
            self.stdout.write("Incidents already exist — skipping incident seeding.")
            return
        scenarios = [
            (
                "Large pothole on main road",
                "road-damage",
                "high",
                IncidentStatus.VERIFIED,
                "Deep pothole causing two-wheeler accidents near the junction.",
            ),
            (
                "Water leakage flooding street",
                "water-leakage",
                "high",
                IncidentStatus.ASSIGNED,
                "Burst pipeline flooding the road; traffic disrupted.",
            ),
            (
                "Garbage not collected for a week",
                "garbage-accumulation",
                "medium",
                IncidentStatus.SUBMITTED,
                "Overflowing bins attracting stray animals.",
            ),
            (
                "Streetlight not working",
                "broken-streetlight",
                "low",
                IncidentStatus.UNDER_REVIEW,
                "Entire stretch dark after 7pm.",
            ),
            (
                "Fire in small warehouse",
                "fire",
                "critical",
                IncidentStatus.ESCALATED,
                "Smoke visible; fire services en route. Emergency.",
            ),
            (
                "Flooding near subway entrance",
                "flooding",
                "critical",
                IncidentStatus.IN_PROGRESS,
                "Waterlogging blocking pedestrian passage.",
            ),
            (
                "Stray dog pack aggressive",
                "stray-animal",
                "medium",
                IncidentStatus.RESOLVED,
                "Pack near school gate; animal control responded.",
            ),
            (
                "Fallen tree blocking lane",
                "road-damage",
                "high",
                IncidentStatus.CLOSED,
                "Tree down after storm; cleared by roads crew.",
            ),
            (
                "Illegal dumping in plot",
                "illegal-dumping",
                "medium",
                IncidentStatus.VERIFIED,
                "Construction debris dumped overnight.",
            ),
            (
                "Noise complaint late night",
                "noise-complaint",
                "low",
                IncidentStatus.REJECTED,
                "Loudspeakers past permitted hours; addressed by caller.",
            ),
            (
                "Traffic signal stuck",
                "traffic-accident",
                "high",
                IncidentStatus.REOPENED,
                "Signal stuck red causing jams and near-misses.",
            ),
            (
                "Exposed electrical wire",
                "electrical-hazard",
                "critical",
                IncidentStatus.ASSIGNED,
                "Live wire hanging at child height.",
            ),
            # Additional incidents for better geographic spread
            (
                "Manhole cover missing on highway",
                "road-damage",
                "critical",
                IncidentStatus.VERIFIED,
                "Open manhole on service lane - immediate danger to vehicles.",
            ),
            (
                "Sewage overflow near market",
                "water-leakage",
                "high",
                IncidentStatus.ASSIGNED,
                "Raw sewage spilling onto pedestrian walkway near vegetable market.",
            ),
            (
                "Construction debris on footpath",
                "illegal-dumping",
                "medium",
                IncidentStatus.SUBMITTED,
                "Building materials blocking wheelchair access on main footpath.",
            ),
            (
                "Dead streetlights on bridge",
                "broken-streetlight",
                "medium",
                IncidentStatus.UNDER_REVIEW,
                "Multiple lights out on river bridge - safety concern at night.",
            ),
            (
                "Transformer sparking in residential area",
                "electrical-hazard",
                "critical",
                IncidentStatus.ESCALATED,
                "Loud buzzing and sparks from transformer box near apartment complex.",
            ),
            (
                "Waterlogging in underpass",
                "flooding",
                "high",
                IncidentStatus.IN_PROGRESS,
                "Knee-deep water in railway underpass after heavy rain.",
            ),
            (
                "Stray cattle blocking traffic",
                "stray-animal",
                "medium",
                IncidentStatus.VERIFIED,
                "Cows resting on main road during peak hours near railway station.",
            ),
            (
                "Cracked footpath tiles - trip hazard",
                "road-damage",
                "low",
                IncidentStatus.SUBMITTED,
                "Broken paving stones causing elderly residents to trip.",
            ),
            (
                "Overflowing community bin",
                "garbage-accumulation",
                "medium",
                IncidentStatus.ASSIGNED,
                "Bin not emptied for 5 days; waste spilling onto road.",
            ),
            (
                "Gas leak smell near restaurant",
                "public-safety-threat",
                "critical",
                IncidentStatus.ESCALATED,
                "Strong gas odor reported by multiple residents near food court.",
            ),
            (
                "Abandoned vehicle in no-parking zone",
                "traffic-accident",
                "low",
                IncidentStatus.VERIFIED,
                "Car parked for 3+ weeks blocking emergency vehicle access.",
            ),
            (
                "Broken park bench with exposed nails",
                "building-damage",
                "medium",
                IncidentStatus.SUBMITTED,
                "Metal bench frame damaged - sharp edges facing playground.",
            ),
            (
                "Mosquito breeding in stagnant water",
                "sanitation",
                "high",
                IncidentStatus.IN_PROGRESS,
                "Construction site water tank uncovered - dengue risk in area.",
            ),
            (
                "Elevator stuck in municipal building",
                "public-safety-threat",
                "high",
                IncidentStatus.ASSIGNED,
                "Senior citizens trapped for 45 mins; maintenance delayed.",
            ),
            (
                "Missing speed breakers near school",
                "road-damage",
                "high",
                IncidentStatus.VERIFIED,
                "Vehicles speeding past school zone; children at risk.",
            ),
            (
                "Clogged storm drain causing backflow",
                "flooding",
                "critical",
                IncidentStatus.IN_PROGRESS,
                "Drain blocked with plastic waste - water entering ground floor flats.",
            ),
            (
                "Illegal banner on pedestrian bridge",
                "public-safety-threat",
                "low",
                IncidentStatus.REJECTED,
                "Political banner blocking walkway - removed by enforcement.",
            ),
            (
                "Street vendor blocking fire exit",
                "fire",
                "medium",
                IncidentStatus.VERIFIED,
                "Food cart parked directly in front of mall emergency exit.",
            ),
            (
                "Pothole cluster on arterial road",
                "road-damage",
                "high",
                IncidentStatus.RESOLVED,
                "Series of potholes over 200m stretch - patched by roads team.",
            ),
            (
                "Water meter leaking in apartment block",
                "water-leakage",
                "medium",
                IncidentStatus.CLOSED,
                "Continuous leak from main meter - meter replaced.",
            ),
            (
                "Flickering lights in subway station",
                "broken-streetlight",
                "low",
                IncidentStatus.RESOLVED,
                "Intermittent lighting causing discomfort to commuters.",
            ),
            (
                "Dumpster fire in alleyway",
                "fire",
                "critical",
                IncidentStatus.CLOSED,
                "Small fire in waste container - quickly contained by fire dept.",
            ),
            (
                "Open excavation without barricades",
                "public-safety-threat",
                "critical",
                IncidentStatus.ESCALATED,
                "Construction pit left unguarded overnight near busy junction.",
            ),
            (
                "Noise from late-night factory",
                "noise-complaint",
                "medium",
                IncidentStatus.REJECTED,
                "Industrial noise within permitted decibel limits per inspection.",
            ),
            (
                "Faded zebra crossing markings",
                "road-damage",
                "medium",
                IncidentStatus.VERIFIED,
                "Pedestrian crossing invisible at night near hospital.",
            ),
            (
                "Broken drain cover in cycle lane",
                "road-damage",
                "high",
                IncidentStatus.ASSIGNED,
                "Cyclist injured by uncovered drain - urgent repair needed.",
            ),
            (
                "Garbage burning causing smoke",
                "garbage-accumulation",
                "medium",
                IncidentStatus.IN_PROGRESS,
                "Municipal workers burning waste - air quality complaint.",
            ),
            (
                "Exposed wiring on streetlight pole",
                "electrical-hazard",
                "critical",
                IncidentStatus.ESCALATED,
                "Live wires at child height after storm damage.",
            ),
            (
                "Blocked ambulance access road",
                "traffic-accident",
                "critical",
                IncidentStatus.VERIFIED,
                "Parked vehicles preventing emergency access to clinic.",
            ),
            (
                "Collapsed boundary wall of park",
                "building-damage",
                "high",
                IncidentStatus.ASSIGNED,
                "Storm-damaged wall - bricks fallen onto jogging track.",
            ),
            (
                "Stray monkeys entering homes",
                "stray-animal",
                "high",
                IncidentStatus.VERIFIED,
                "Troop of monkeys damaging property in residential colony.",
            ),
        ]
        for idx, (title, cat_slug, severity, status, description) in enumerate(scenarios):
            citizen = self.citizens[idx % len(self.citizens)]
            ward = self.wards[idx % len(self.wards)]
            category = self.categories[cat_slug]
            created = timezone.now() - timedelta(
                days=random.randint(0, 20), hours=random.randint(0, 20)
            )
            incident = Incident(
                title=title,
                description=description,
                category=category,
                severity=severity,
                status=status,
                reporter=citizen,
                department=category.default_department,
                ward=ward,
                latitude=SEED_LAT + random.uniform(-0.04, 0.04),
                longitude=SEED_LNG + random.uniform(-0.04, 0.04),
                address_public=f"Near {ward.name} landmark {idx + 1}",
                address_private=f"{random.randint(1, 200)} Fake Street, {ward.name}",
                is_emergency=severity == "critical",
                created_at=created,
                updated_at=created,
            )
            if status != IncidentStatus.SUBMITTED:
                incident.submitted_at = created
            if status in (
                IncidentStatus.VERIFIED,
                IncidentStatus.ASSIGNED,
                IncidentStatus.IN_PROGRESS,
                IncidentStatus.ESCALATED,
                IncidentStatus.RESOLVED,
                IncidentStatus.CLOSED,
                IncidentStatus.REOPENED,
            ):
                incident.verified_at = created + timedelta(hours=2)
            if status in (
                IncidentStatus.ASSIGNED,
                IncidentStatus.IN_PROGRESS,
                IncidentStatus.ESCALATED,
                IncidentStatus.RESOLVED,
                IncidentStatus.CLOSED,
                IncidentStatus.REOPENED,
            ):
                incident.assigned_at = created + timedelta(hours=4)
                incident.assigned_staff = (
                    self.staff.get(category.default_department.code)
                    if category.default_department
                    else None
                )
            if status in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED):
                incident.resolved_at = created + timedelta(days=2)
                incident.resolution_summary = "Issue inspected and fixed by field team."
            if status == IncidentStatus.CLOSED:
                incident.closed_at = created + timedelta(days=3)
                incident.satisfaction_rating = random.randint(3, 5)
                incident.citizen_confirmed_resolution = True
            incident.sla_deadline = created + timedelta(
                hours={"low": 120, "medium": 72, "high": 24, "critical": 6}[severity]
            )
            incident.sla_breached = (
                status not in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED)
                and timezone.now() > incident.sla_deadline
            )
            incident.save()

            if status == IncidentStatus.RESOLVED and idx == 6:
                IncidentComment.objects.create(
                    incident=incident,
                    author=self.staff.get("health"),
                    body="Animal control team visited; area cleared.",
                    is_internal=False,
                )

        self.stdout.write(f"  {Incident.objects.count()} incidents created")

    def _announcements(self):
        admin = getattr(self, "admin", None) or User.objects.filter(
            role=UserRole.SUPERUSER
        ).first()
        now = timezone.now()
        samples = [
            {
                "title": "Welcome to SafeCity",
                "body": (
                    "Report civic issues in your area and track their resolution in real "
                    "time.\n\nHow it works:\n1. Pin the problem on the map\n2. City staff "
                    "verify and route it to the right department\n3. You get updates at "
                    "every step and confirm when it's fixed"
                ),
                "audience": "public",
                "is_pinned": True,
                "published_at": now - timedelta(days=30),
            },
            {
                "title": "Monsoon preparedness drive — report waterlogging early",
                "body": (
                    "The monsoon season is here. Early reports help us deploy pumps and "
                    "clear drains before flooding spreads.\n\nDuring monsoon weeks, "
                    "water-related emergency categories are automatically prioritized and "
                    "escalate faster if SLA deadlines slip.\n\nIf you see a choked drain, "
                    "report it under \"Water & Drainage\" and attach a photo if safe to do "
                    "so. Never enter flooded areas to take pictures."
                ),
                "audience": "public",
                "published_at": now - timedelta(days=6),
            },
            {
                "title": "Ward 12 — resurfacing work from Monday",
                "body": (
                    "Road resurfacing starts Monday on the Ward 12 arterial stretch. "
                    "Pothole reports in this zone will be batched into the resurfacing "
                    "plan and may show as \"In Progress\" sooner than usual.\n\nExpect "
                    "traffic diversions between 8 AM and 6 PM for the rest of the week."
                ),
                "audience": "public",
                "published_at": now - timedelta(days=3),
            },
            {
                "title": "Streetlight replacement programme completed in Ward 7",
                "body": (
                    "All 412 reported streetlight faults in Ward 7 have been repaired. "
                    "Thank you for the reports — they made the audit possible.\n\nIf a "
                    "light is still out, reopen the original report instead of filing a "
                    "new one so the crew returns to the same location."
                ),
                "audience": "public",
                "published_at": now - timedelta(days=1),
            },
        ]
        for sample in samples:
            Announcement.objects.get_or_create(
                title=sample["title"],
                defaults={
                    "body": sample["body"],
                    "audience": sample["audience"],
                    "is_published": True,
                    "is_pinned": sample.get("is_pinned", False),
                    "published_at": sample["published_at"],
                    "published_by": admin,
                },
            )
