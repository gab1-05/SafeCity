import { useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useQuery } from "@tanstack/react-query";
import { StatusBadge, SeverityBadge } from "@/components/incident/Badges";
import { Button } from "@/components/ui/button";
import { STATUS_LABELS, type Incident, type IncidentStatus, type Severity } from "@/types";
import { formatDate, cn } from "@/lib/utils";
import { Filter, X, ChevronDown, ChevronUp, MapPin, Circle, Zap, Users } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Select } from "@/components/ui/input";
import { wsService } from "@/services/websocket";
import { incidentsApi, referenceDataApi, MAP_ACTIVE_STATUSES, isVisibleOnMap } from "@/api/incidents";

const MUMBAI_CENTER: [number, number] = [19.076, 72.8777];

/** Great-circle distance in km (the list API has no geo support, so the
 * nearby page measures client-side from the device location). */
function haversineKm(aLat: number, aLng: number, bLat: number, bLng: number): number {
  const R = 6371;
  const dLat = ((bLat - aLat) * Math.PI) / 180;
  const dLng = ((bLng - aLng) * Math.PI) / 180;
  const s =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((aLat * Math.PI) / 180) * Math.cos((bLat * Math.PI) / 180) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(s));
}

const CATEGORY_COLORS: Record<string, string> = {
  roads: "#f59e0b",
  "road-damage": "#f59e0b",
  "traffic-accident": "#ef4444",
  water: "#2563eb",
  "water-leakage": "#2563eb",
  flooding: "#0ea5e9",
  electricity: "#dc2626",
  "broken-streetlight": "#eab308",
  "electrical-hazard": "#dc2626",
  fire: "#ea580c",
  "solid-waste": "#16a34a",
  "garbage-accumulation": "#16a34a",
  "illegal-dumping": "#15803d",
  sanitation: "#0d9488",
  "public-safety": "#7c3aed",
  "public-safety-threat": "#7c3aed",
  "medical-emergency": "#db2777",
  "noise-complaint": "#9333ea",
  "building-damage": "#92400e",
  other: "#6b7280",
};

const FALLBACK_COLOR = "#1b6f8b";

function colorForCategory(slug: string | undefined): string {
  if (!slug) return FALLBACK_COLOR;
  return CATEGORY_COLORS[slug] ?? FALLBACK_COLOR;
}

const SEVERITY_RING: Record<Severity, string> = {
  low: "#ffffff",
  medium: "#ffffff",
  high: "#fbbf24",
  critical: "#ef4444",
};

function pinIcon(categorySlug: string | undefined, severity: Severity, isActive: boolean) {
  const fill = colorForCategory(categorySlug);
  const ring = SEVERITY_RING[severity];
  const size = isActive ? 30 : 24;
  const inner = isActive ? 13 : 10;
  return L.divIcon({
    className: "",
    html: `<div style="width:${size}px;height:${size}px;border-radius:50% 50% 50% 0;
      transform:rotate(-45deg);background:${fill};border:${isActive ? 3 : 2}px solid ${ring};
      box-shadow:${isActive ? "0 0 0 5px rgba(27,111,139,.22)," : ""}0 2px 8px rgba(0,0,0,.4);">
      <span style="position:absolute;width:${inner}px;height:${inner}px;border-radius:999px;background:white;left:50%;top:50%;transform:translate(-50%,-50%);opacity:.95"></span>
    </div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size],
  });
}

function FitBounds({ points }: { points: Array<[number, number]> }) {
  const map = useMap();
  useEffect(() => {
    if (points.length > 1) {
      map.fitBounds(L.latLngBounds(points).pad(0.2));
    }
  }, [points, map]);
  return null;
}

function UserLocationMarker({ position }: { position: [number, number] }) {
  return (
    <Marker position={position} icon={L.divIcon({
      className: "",
      html: `<div style="width:20px;height:20px;border-radius:50%;background:#3b82f6;border:3px solid white;box-shadow:0 0 0 3px #3b82f6,0 2px 8px rgba(0,0,0,.3)"></div>`,
      iconSize: [20, 20],
      iconAnchor: [10, 10],
    })} />
  );
}

interface NearbyIncident {
  id: string;
  reference_number: string;
  title: string;
  status: IncidentStatus;
  severity: Severity;
  category: { slug: string; name: string } | null;
  ward_name: string | null;
  address_public: string | null;
  latitude: number;
  longitude: number;
  created_at: string;
  resolved_at: string | null;
  is_emergency: boolean;
  distance_km: number;
}

export function NearbyIncidentsPage() {
  const [userLocation, setUserLocation] = useState<[number, number] | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(true);
  const [radiusKm, setRadiusKm] = useState(5);
  const [status, setStatus] = useState("");
  const [severity, setSeverity] = useState("");
  const [category, setCategory] = useState("");

  // Geolocation
  useEffect(() => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (pos) => setUserLocation([pos.coords.latitude, pos.coords.longitude]),
      () => setUserLocation(MUMBAI_CENTER)
    );
  }, []);

  // Fetch nearby incidents: all active + new reports, plus recently
  // resolved (which disappear after RESOLVED_VISIBLE_DAYS). scope=public
  // gives this view even while logged in (citizens otherwise see only own).
  const { data, isPending, refetch } = useQuery({
    queryKey: ["nearby-incidents", userLocation, radiusKm, status, severity, category],
    queryFn: async () => {
      if (!userLocation) return { results: [] as Incident[], count: 0, next: null, previous: null };
      return incidentsApi.list({
        status: status ? [status] : [...MAP_ACTIVE_STATUSES, "resolved"],
        scope: "public",
        page_size: 100,
      });
    },
    enabled: !!userLocation,
    refetchInterval: 60_000,
  });

  // WebSocket for live updates
  useEffect(() => {
    const unsubscribe = wsService.on("notification", () => {
      void refetch();
    });
    const unsubscribeIncident = wsService.on("incident_update", () => {
      void refetch();
    });
    return () => {
      unsubscribe();
      unsubscribeIncident();
    };
  }, [refetch]);

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: referenceDataApi.categories,
  });

  const incidents = useMemo((): NearbyIncident[] => {
    const source = data?.results ?? [];
    if (!userLocation) return [];
    return source
      .filter((incident: Incident) => {
        if (!isVisibleOnMap(incident)) return false;
        const statusMatch = !status || incident.status === status;
        const severityMatch = !severity || incident.severity === severity;
        const categoryMatch = !category || incident.category?.slug === category;
        return statusMatch && severityMatch && categoryMatch;
      })
      .map((incident: Incident) => ({
        ...incident,
        distance_km:
          (incident as Incident & { distance_km?: number }).distance_km ??
          haversineKm(userLocation[0], userLocation[1], Number(incident.latitude), Number(incident.longitude)),
      }))
      .filter((incident: NearbyIncident) => incident.distance_km <= radiusKm)
      .sort((a: NearbyIncident, b: NearbyIncident) => a.distance_km - b.distance_km);
  }, [data?.results, userLocation, radiusKm, status, severity, category]);

  const { points, byColor } = useMemo(() => {
    const pts: Array<[number, number]> = [];
    const counts: Record<string, number> = {};
    for (const i of incidents) {
      pts.push([Number(i.latitude), Number(i.longitude)]);
      const key = i.category?.slug ?? "other";
      counts[key] = (counts[key] ?? 0) + 1;
    }
    return { points: pts, byColor: counts };
  }, [incidents]);

  const legendCategories = Object.entries(CATEGORY_COLORS).filter(([slug]) => byColor[slug]);
  const extraCount = byColor["other"] ?? 0;

  const hasActiveFilters = status || severity || category || radiusKm !== 5;

  const clearFilters = () => {
    setStatus("");
    setSeverity("");
    setCategory("");
    setRadiusKm(5);
  };

  if (!userLocation) {
    return (
      <div className="container py-8 flex items-center justify-center h-[60vh]">
        <div className="text-center">
          <MapPin className="mx-auto h-12 w-12 text-muted-foreground/50" />
          <p className="mt-4 text-muted-foreground">Locating you…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container py-8">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold">
            <MapPin className="h-6 w-6 text-primary" aria-hidden />
            Incidents near you
          </h1>
          <p className="text-sm text-muted-foreground">
            Live updates via WebSocket. Showing incidents within {radiusKm}km of your location.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center gap-2"
          >
            <Filter className="h-4 w-4" />
            Filters
            {showFilters ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
          {hasActiveFilters && (
            <Button variant="ghost" size="sm" onClick={clearFilters} className="flex items-center gap-1">
              <X className="h-4 w-4" />
              Clear
            </Button>
          )}
        </div>
      </div>

      {showFilters && (
        <Card className="mb-6 animate-slide-down">
          <CardContent className="pt-6">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
              <div className="space-y-1.5">
                <label className="text-sm font-medium" htmlFor="radius-filter">Radius</label>
                <Select
                  id="radius-filter"
                  value={String(radiusKm)}
                  onChange={(e) => setRadiusKm(Number(e.target.value))}
                  className="w-full"
                >
                  <option value="1">1 km</option>
                  <option value="2">2 km</option>
                  <option value="5">5 km</option>
                  <option value="10">10 km</option>
                </Select>
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium" htmlFor="status-filter">Status</label>
                <Select
                  id="status-filter"
                  value={status}
                  onChange={(e) => setStatus(e.target.value)}
                  className="w-full"
                >
                  <option value="">All</option>
                  {([...MAP_ACTIVE_STATUSES, "resolved"] as IncidentStatus[]).map((s) => (
                    <option key={s} value={s}>{STATUS_LABELS[s] ?? s}</option>
                  ))}
                </Select>
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium" htmlFor="severity-filter">Severity</label>
                <Select
                  id="severity-filter"
                  value={severity}
                  onChange={(e) => setSeverity(e.target.value)}
                  className="w-full"
                >
                  <option value="">All</option>
                  {(["low", "medium", "high", "critical"] as Severity[]).map((s) => (
                    <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
                  ))}
                </Select>
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium" htmlFor="category-filter">Category</label>
                <Select
                  id="category-filter"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full"
                >
                  <option value="">All</option>
                  {categories?.map((item) => (
                    <option key={item.id} value={item.slug}>{item.name}</option>
                  ))}
                </Select>
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Legend</label>
                <div className="flex flex-wrap gap-2">
                  <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                    <Circle className="h-3 w-3 text-primary" /> You
                  </span>
                  <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                    <Zap className="h-3 w-3 text-warning" /> Emergency
                  </span>
                  <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                    <Users className="h-3 w-3 text-success" /> Resolved
                  </span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
        <div className="relative h-[600px] overflow-hidden rounded-lg border">
          <MapContainer center={userLocation} zoom={13} className="h-full w-full">
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <FitBounds points={[userLocation, ...points]} />
            <UserLocationMarker position={userLocation} />
            {incidents.map((incident) => (
              <Marker
                key={incident.id}
                position={[Number(incident.latitude), Number(incident.longitude)]}
                icon={pinIcon(incident.category?.slug, incident.severity, incident.id === activeId)}
                eventHandlers={{ click: () => setActiveId(incident.id) }}
              >
                <Popup>
                  <div className="min-w-[240px] space-y-2">
                    <div className="flex flex-wrap gap-1">
                      <StatusBadge status={incident.status} />
                      <SeverityBadge severity={incident.severity} />
                      {incident.is_emergency && (
                        <span className="rounded-full bg-danger/15 px-2 py-0.5 text-xs font-semibold text-danger">
                          Emergency
                        </span>
                      )}
                      <span className="rounded-full bg-primary/15 px-2 py-0.5 text-xs font-semibold text-primary">
                        {incident.distance_km.toFixed(1)} km
                      </span>
                    </div>
                    <strong>{incident.title}</strong>
                    <p className="text-xs text-muted-foreground">
                      {incident.category?.name} · {incident.ward_name ?? "—"} · {formatDate(incident.created_at)}
                    </p>
                    {incident.address_public && (
                      <p className="text-xs">📍 {incident.address_public}</p>
                    )}
                    {incident.status === "resolved" && incident.resolved_at && (
                      <p className="text-xs text-success">
                        Resolved {formatDate(incident.resolved_at)}
                      </p>
                    )}
                    <a
                      href={`/track?ref=${incident.reference_number}`}
                      className="text-xs font-medium text-primary underline"
                    >
                      Track {incident.reference_number} →
                    </a>
                  </div>
                </Popup>
              </Marker>
            ))}
          </MapContainer>

          {/* Legend */}
          <div className="absolute bottom-3 left-3 z-[1000] rounded-lg border bg-card/95 p-3 shadow-md max-h-64 overflow-y-auto">
            <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Categories</p>
            <ul className="space-y-1">
              {legendCategories.map(([slug, color]) => (
                <li key={slug} className="flex items-center gap-2 text-xs">
                  <span
                    className="inline-block h-3 w-3 rounded-full"
                    style={{ backgroundColor: color }}
                    aria-hidden
                  />
                  <span className="capitalize truncate max-w-[140px]">{slug.replace(/-/g, " ")}</span>
                  <span className="text-muted-foreground">({byColor[slug]})</span>
                </li>
              ))}
              {extraCount > 0 && (
                <li className="flex items-center gap-2 text-xs">
                  <span
                    className="inline-block h-3 w-3 rounded-full"
                    style={{ backgroundColor: FALLBACK_COLOR }}
                    aria-hidden
                  />
                  Other <span className="text-muted-foreground">({extraCount})</span>
                </li>
              )}
            </ul>
            <div className="mt-2 border-t pt-2">
              <p className="flex items-center gap-2 text-xs text-muted-foreground">
                <span className="inline-block h-3 w-3 rounded-full border-2 border-[#ef4444] bg-card" aria-hidden />
                ring = high / critical severity
              </p>
            </div>
          </div>
        </div>

        {/* Sidebar - Incident List */}
        <div className="space-y-4 max-h-[600px] overflow-y-auto pr-2 scrollbar-thin">
          {isPending && [1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="pt-6">
                <div className="h-4 w-3/4 bg-muted rounded mb-2" />
                <div className="h-3 w-1/2 bg-muted rounded" />
              </CardContent>
            </Card>
          ))}

          {!isPending && incidents.length === 0 && (
            <Card className="text-center py-12">
              <CardContent>
                <MapPin className="mx-auto h-12 w-12 text-muted-foreground/50" />
                <p className="mt-4 text-muted-foreground">No incidents in this area</p>
                <p className="text-sm text-muted-foreground/70">Try increasing the radius or adjusting filters</p>
              </CardContent>
            </Card>
          )}

          {!isPending && incidents.length > 0 && (
            <>
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span>{incidents.length} incident{incidents.length !== 1 ? "s" : ""} found</span>
                <Button variant="ghost" size="sm" onClick={() => { void refetch(); }} className="gap-1">
                  <ChevronDown className="h-4 w-4" />
                  Refresh
                </Button>
              </div>
              <div className="space-y-2">
                {incidents.map((incident) => (
                  <Card
                    key={incident.id}
                    className={cn(
                      "cursor-pointer transition-all",
                      incident.id === activeId && "border-primary/50 bg-primary/5"
                    )}
                    onClick={() => setActiveId(incident.id === activeId ? null : incident.id)}
                  >
                    <CardContent className="pt-4 pb-4">
                      <div className="flex items-start gap-3">
                        <div className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-lg"
                          style={{ backgroundColor: incident.category
                            ? `hsl(var(--severity-${incident.severity}))`
                            : "hsl(var(--muted))" }}>
                          <SeverityBadge severity={incident.severity} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <p className="font-medium truncate">{incident.title}</p>
                            <StatusBadge status={incident.status} />
                            {incident.is_emergency && (
                              <span className="rounded-full bg-danger/15 px-1.5 py-0.5 text-[10px] font-semibold text-danger">
                                Emergency
                              </span>
                            )}
                          </div>
                          <p className="mt-1 text-xs text-muted-foreground truncate">
                            {incident.category?.name} · {incident.ward_name ?? "—"} · {incident.distance_km.toFixed(1)} km away
                          </p>
                          <p className="mt-1 text-xs text-muted-foreground">{formatDate(incident.created_at)}</p>
                        </div>
                        <ChevronDown className="h-5 w-5 text-muted-foreground shrink-0" />
                      </div>
                      {incident.id === activeId && (
                        <div className="mt-3 pt-3 border-t space-y-2 animate-slide-down">
                          {incident.address_public && (
                            <p className="text-xs text-muted-foreground flex items-center gap-1">
                              <MapPin className="h-3 w-3" /> {incident.address_public}
                            </p>
                          )}
                          {incident.status === "resolved" && incident.resolved_at && (
                            <p className="text-xs text-success flex items-center gap-1">
                              <Circle className="h-3 w-3" /> Resolved {formatDate(incident.resolved_at)}
                            </p>
                          )}
                          <a
                            href={`/track?ref=${incident.reference_number}`}
                            className="text-xs font-medium text-primary underline flex items-center gap-1"
                          >
                            Track {incident.reference_number} →
                          </a>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}