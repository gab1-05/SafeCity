"""SafeCity load test (Locust) — free capacity measurement.

Run against Compose or kind (both $0):

    pip install -r scripts/requirements-load.txt
    locust -f scripts/locustfile.py --host http://localhost:18081
    # open http://localhost:8089, set users/rate, start

Headless example (50 users, 5/s spawn, 5 minutes):

    locust -f scripts/locustfile.py --host http://localhost:18081 \\
        --headless -u 50 -r 5 -t 5m --csv results/safecity

Requires seeded demo data (make seed). Incident creation is rate-limited
(RATE_LIMIT_INCIDENTS_PER_HOUR); 429s are counted as expected, not failures.
"""

import random

from locust import HttpUser, between, task

CITIZENS = [f"citizen{i}@safecity.local" for i in range(1, 6)]
CITIZEN_PASSWORD = "Citizen@12345!"
STAFF_EMAIL = "staff.water@safecity.local"
STAFF_PASSWORD = "Staff@12345!"

CATEGORIES_FALLBACK = ["road-damage", "flooding", "broken-streetlight"]


class CitizenUser(HttpUser):
    """Reads own reports, tracks, and files new incidents (rate-limited)."""

    wait_time = between(1, 3)
    weight = 5

    def on_start(self):
        r = self.client.post(
            "/api/v1/auth/token/",
            json={"email": random.choice(CITIZENS), "password": CITIZEN_PASSWORD},
            name="login",
        )
        r.raise_for_status()
        self.token = r.json()["access"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        cats = self.client.get("/api/v1/categories/", headers=self.headers, name="categories")
        try:
            results = cats.json().get("results", cats.json())
            self.category_ids = [c["id"] for c in results[:5]] or []
        except Exception:
            self.category_ids = []

    @task(5)
    def my_incidents(self):
        self.client.get("/api/v1/incidents/?page_size=25", headers=self.headers, name="my_incidents")

    @task(3)
    def public_map(self):
        self.client.get(
            "/api/v1/incidents/?scope=public&page_size=200",
            headers=self.headers,
            name="public_map",
        )

    @task(2)
    def notifications(self):
        self.client.get("/api/v1/notifications/", headers=self.headers, name="notifications")

    @task(1)
    def report_incident(self):
        if not self.category_ids:
            return
        with self.client.post(
            "/api/v1/incidents/",
            headers=self.headers,
            json={
                "title": f"Load test pothole {random.randint(1000, 9999)}",
                "description": "Pothole reported by the Locust load test script.",
                "category_id": random.choice(self.category_ids),
                "severity": "medium",
                "urgency": "normal",
                "latitude": round(19.076 + random.uniform(-0.05, 0.05), 6),
                "longitude": round(72.8777 + random.uniform(-0.05, 0.05), 6),
                "address_public": "Load test junction",
            },
            name="report_incident",
            catch_response=True,
        ) as resp:
            # Creation is throttled per user/hour — 429 is expected load, not failure.
            if resp.status_code in (201, 429):
                resp.success()


class StaffUser(HttpUser):
    """Triage queue + analytics, the authority hot path."""

    wait_time = between(1, 3)
    weight = 3

    def on_start(self):
        r = self.client.post(
            "/api/v1/auth/token/",
            json={"email": STAFF_EMAIL, "password": STAFF_PASSWORD},
            name="login",
        )
        r.raise_for_status()
        self.headers = {"Authorization": f"Bearer {r.json()['access']}"}

    @task(5)
    def queue(self):
        self.client.get(
            "/api/v1/incidents/?page_size=25&status=submitted",
            headers=self.headers,
            name="queue",
        )

    @task(2)
    def analytics(self):
        self.client.get(
            "/api/v1/analytics/summary/?days=30", headers=self.headers, name="analytics"
        )


class PublicUser(HttpUser):
    """Unauthenticated baseline: health + public map (what evaluators hit)."""

    wait_time = between(1, 2)
    weight = 2

    @task(3)
    def health(self):
        self.client.get("/api/health/", name="health")

    @task(5)
    def public_map(self):
        self.client.get("/api/v1/incidents/?scope=public&page_size=200", name="public_map_anon")

    @task(1)
    def announcements(self):
        self.client.get("/api/v1/announcements/", name="announcements")
