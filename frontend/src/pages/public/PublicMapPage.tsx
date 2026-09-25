import { useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { incidentsApi, referenceDataApi } from "@/api/incidents";
import { useQuery } from "@tanstack/react-query";
import { StatusBadge, SeverityBadge } from "@/components/incident/Badges";
import { Select } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { STATUS_LABELS, type IncidentStatus, type Severity } from "@/types";
import { formatDate } from "@/lib/utils";
import { Filter, X, ChevronDown, ChevronUp, Calendar, MapPin, AlertTriangle } from "lucide-react";

const MUMBAI_CENTER: [number, number] = [19.076, 72.8777];

/** Category → pin color (dot fill). Keys match seeded category slugs. */
const CATEGORY_COLORS: Record<string, string> = {
  roads: "#f59e0b", // amber — potholes, obstructions
  "road-damage": "#f59e0b",
  "traffic-accident": "#ef4444",
  water: "#2563eb", // blue — flooding, leaks
  "water-leakage": "#2563eb",
  flooding: "#0ea5e9",
  electricity: "#dc2626", // red — streetlights, wiring
  "broken-streetlight": "#eab308",
  "electrical-hazard": "#dc2626",
  fire: "#ea580c", // deep orange
  "solid-waste": "#16a34a", // green — garbage, dumping
  "garbage-accumulation": "#16a34a",
  "illegal-dumping": "#15803d",
  sanitation: "#0d9488", // teal
  "public-safety": "#7c3aed", // violet
  "public-safety-threat": "#7c3aed",
  "medical-emergency": "#db2777",
  "noise-complaint": "#9333ea",
  "building-damage": "#92400e",
  other: "#6b7280", // gray
};

const FALLBACK_COLOR = "#1b6f8b";

function colorForCategory(slug: string | undefined): string {
  if (!slug) return FALLBACK_COLOR;
  return CATEGORY_COLORS[slug] ?? FALLBACK_COLOR;
}

/** Severity changes the pin's border — visible at a glance even when zoomed out. */
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

export function PublicMapPage() {
  const [status, setStatus] = useState<string>("");
  const [activeId, setActiveId] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(true);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [severity, setSeverity] = useState("");
  const [category, setCategory] = useState("");
  const [ward, setWard] = useState("");

  const { data, isPending, isError, refetch } = useQuery({
    queryKey: ["public-map", status, category, ward, severity, dateFrom, dateTo],
    queryFn: () =>
      incidentsApi.list({
        status: status ? [status] : ["verified", "resolved"],
        page_size: 200,
      }),
  });

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: referenceDataApi.categories,
  });

  const { data: wards } = useQuery({
    queryKey: ["wards"],
    queryFn: referenceDataApi.wards,
  });

  const incidents = useMemo(() => {
    const source = data?.results ?? [];
    return source.filter((incident) => {
      const categoryMatch = !category || incident.category?.slug === category;
      const wardMatch = !ward || incident.ward_name === wards?.find((w) => w.code === ward)?.name;
      const severityMatch = !severity || incident.severity === severity;
      const dateFromMatch = !dateFrom || new Date(incident.created_at) >= new Date(dateFrom);
      const dateToMatch = !dateTo || new Date(incident.created_at) <= new Date(dateTo);
      return categoryMatch && wardMatch && severityMatch && dateFromMatch && dateToMatch;
    });
  }, [category, data?.results, ward, wards, severity, dateFrom, dateTo]);

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

  const hasActiveFilters = status || category || ward || severity || dateFrom || dateTo;

  const clearFilters = () => {
    setStatus("");
    setCategory("");
    setWard("");
    setSeverity("");
    setDateFrom("");
    setDateTo("");
  };

  return (
    <div className="container py-8">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Public incident map</h1>
          <p className="text-sm text-muted-foreground">
            Verified and resolved incidents. Locations are approximate to protect privacy.
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
        <div className="mb-6 rounded-lg border bg-card p-4 animate-slide-down">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-6">
            <div className="space-y-1.5">
              <label className="text-sm font-medium" htmlFor="status-filter">Status</label>
              <Select
                id="status-filter"
                aria-label="Filter by status"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="w-full"
              >
                <option value="">All public</option>
                {(["verified", "resolved"] as IncidentStatus[]).map((s) => (
                  <option key={s} value={s}>
                    {STATUS_LABELS[s]}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium" htmlFor="severity-filter">Severity</label>
              <Select
                id="severity-filter"
                aria-label="Filter by severity"
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
                className="w-full"
              >
                <option value="">All severities</option>
                {(["low", "medium", "high", "critical"] as Severity[]).map((s) => (
                  <option key={s} value={s}>
                    {s.charAt(0).toUpperCase() + s.slice(1)}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium" htmlFor="category-filter">Category</label>
              <Select
                id="category-filter"
                aria-label="Filter by category"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full"
              >
                <option value="">All categories</option>
                {categories?.map((item) => (
                  <option key={item.id} value={item.slug}>
                    {item.name}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium" htmlFor="ward-filter">Ward</label>
              <Select
                id="ward-filter"
                aria-label="Filter by ward"
                value={ward}
                onChange={(e) => setWard(e.target.value)}
                className="w-full"
              >
                <option value="">All wards</option>
                {wards?.map((item) => (
                  <option key={item.id} value={item.code}>
                    {item.name}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium" htmlFor="date-from">From Date</label>
              <input
                id="date-from"
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="input-base"
                aria-label="Filter from date"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium" htmlFor="date-to">To Date</label>
              <input
                id="date-to"
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="input-base"
                aria-label="Filter to date"
              />
            </div>
          </div>
          <div className="mt-4 flex items-center gap-2 text-sm text-muted-foreground">
            <span className="flex items-center gap-1">
              <AlertTriangle className="h-3.5 w-3.5" />
              {incidents.length} incident{incidents.length !== 1 ? "s" : ""} shown
            </span>
          </div>
        </div>
      )}

      <div className="relative h-[520px] overflow-hidden rounded-lg border">
        <MapContainer center={MUMBAI_CENTER} zoom={11} className="h-full w-full">
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <FitBounds points={points} />
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
                  </div>
                  <strong>{incident.title}</strong>
                  <p className="text-xs text-muted-foreground">
                    {incident.category?.name} · {incident.ward_name ?? "—"} · reported{" "}
                    {formatDate(incident.created_at)}
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
        <div className="absolute bottom-3 left-3 z-[1000] rounded-lg border bg-card/95 p-3 shadow-md">
          <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Legend
          </p>
          <ul className="space-y-1">
            {legendCategories.map(([slug, color]) => (
              <li key={slug} className="flex items-center gap-2 text-xs">
                <span
                  className="inline-block h-3 w-3 rounded-full"
                  style={{ backgroundColor: color }}
                  aria-hidden
                />
                <span className="capitalize">{slug.replace(/-/g, " ")}</span>
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

      {isPending && <p className="mt-2 text-sm text-muted-foreground">Loading incidents…</p>}
      {!isPending && incidents.length === 0 && (
        <p className="mt-2 text-sm text-muted-foreground">
          No public incidents to display yet.
        </p>
      )}
    </div>
  );
}
