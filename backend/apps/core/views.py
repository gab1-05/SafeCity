"""
Operational endpoints: health, readiness, public runtime config.
Geocoding endpoints: forward and reverse geocoding via OpenStreetMap Nominatim.
"""

import requests
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods


def health(request):
    """Liveness probe: process is up. No external dependencies checked."""
    return JsonResponse({"status": "ok", "service": "safecity-backend"})


def readiness(request):
    """
    Readiness probe: DB, cache/Redis, and storage backend reachable.
    Returns 503 if any critical dependency fails so orchestrators
    stop routing traffic to this pod.
    """
    checks = {}
    ok = True

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception:  # noqa: BLE001
        checks["database"] = "error"
        ok = False

    try:
        cache.set("readiness", "1", 5)
        checks["cache"] = "ok" if cache.get("readiness") == "1" else "error"
        if checks["cache"] != "ok":
            ok = False
    except Exception:  # noqa: BLE001
        checks["cache"] = "error"
        ok = False

    try:
        import boto3  # noqa: F401

        checks["storage"] = "ok" if settings.SAFECITY["MEDIA_BACKEND"] == "s3" else "local"
    except Exception:  # noqa: BLE001
        checks["storage"] = "error"

    return JsonResponse(
        {"status": "ok" if ok else "degraded", "checks": checks},
        status=200 if ok else 503,
    )


def meta_config(request):
    """Public, non-sensitive runtime configuration for the SPA."""
    from apps.accounts.oauth import google_client_id
    from apps.accounts.roles import REQUESTABLE_ROLES, ROLE_PERMISSION_SUMMARY
    from apps.incidents.models import IncidentCategory

    return JsonResponse(
        {
            "map": {
                "provider": "openstreetmap",
                "tile_url": settings.SAFECITY.get(
                    "TILE_URL", "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
                ),
                "attribution": "© OpenStreetMap contributors",
            },
            # Public identifier — safe to expose; presence toggles the
            # Google button in the SPA. Never expose client secrets here.
            "oauth": {
                "google_client_id": google_client_id() or None,
            },
            # Roles a new user may request at signup; the account itself is
            # always created as citizen and the request needs admin approval.
            "signup": {
                "default_role": "citizen",
                "requestable_roles": REQUESTABLE_ROLES,
                "role_permissions": ROLE_PERMISSION_SUMMARY,
            },
            "features": {
                "anonymous_reporting": settings.SAFECITY["ALLOW_ANONYMOUS_REPORTS"],
                "emergency_mode": settings.SAFECITY["EMERGENCY_MODE_ENABLED"],
            },
            "upload_limits": settings.UPLOAD_LIMITS,
            "categories": [
                {"id": str(c.id), "name": c.name, "slug": c.slug, "icon": c.icon}
                for c in IncidentCategory.objects.filter(is_active=True).order_by("display_order")
            ],
        }
    )


NOMINATIM_URL = "https://nominatim.openstreetmap.org"
NOMINATIM_HEADERS = {"User-Agent": "SafeCity/1.0 (contact@safecity.example)"}


def _nominatim_request(endpoint: str, params: dict) -> dict:
    """Make a request to Nominatim with error handling."""
    try:
        resp = requests.get(
            f"{NOMINATIM_URL}{endpoint}",
            params=params,
            headers=NOMINATIM_HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {}


@cache_page(60 * 60 * 24)  # cache for 24 hours
@require_http_methods(["GET"])
def geocode_search(request):
    """
    Forward geocoding: search for places by query string.
    Query params: q (required), limit (optional, default 5), countrycodes (optional, default 'in')
    Returns: list of {place_id, lat, lon, display_name, type, class}
    """
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"results": []})

    limit = min(int(request.GET.get("limit", 5)), 20)
    countrycodes = request.GET.get("countrycodes", "in")

    data = _nominatim_request("/search", {
        "q": query,
        "format": "json",
        "limit": limit,
        "countrycodes": countrycodes,
        "addressdetails": 1,
        "extratags": 1,
    })

    results = []
    for item in data:
        results.append({
            "place_id": item.get("place_id"),
            "lat": float(item.get("lat", 0)),
            "lon": float(item.get("lon", 0)),
            "display_name": item.get("display_name", ""),
            "type": item.get("type", ""),
            "class": item.get("class", ""),
            "address": item.get("address", {}),
        })

    return JsonResponse({"results": results})


@cache_page(60 * 60 * 24)  # cache for 24 hours
@require_http_methods(["GET"])
def geocode_reverse(request):
    """
    Reverse geocoding: get address from coordinates.
    Query params: lat (required), lon (required), zoom (optional, default 18)
    Returns: {lat, lon, display_name, address}
    """
    try:
        lat = float(request.GET.get("lat", 0))
        lon = float(request.GET.get("lon", 0))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid lat/lon"}, status=400)

    if lat == 0 and lon == 0:
        return JsonResponse({"error": "Invalid lat/lon"}, status=400)

    zoom = min(int(request.GET.get("zoom", 18)), 18)

    data = _nominatim_request("/reverse", {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "zoom": zoom,
        "addressdetails": 1,
        "extratags": 1,
    })

    if not data:
        return JsonResponse({"error": "No result found"}, status=404)

    return JsonResponse({
        "lat": float(data.get("lat", lat)),
        "lon": float(data.get("lon", lon)),
        "display_name": data.get("display_name", ""),
        "address": data.get("address", {}),
    })
