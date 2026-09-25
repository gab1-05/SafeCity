import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  Camera,
  Check,
  ChevronLeft,
  ChevronRight,
  Crosshair,
  MapPin,
  Search,
  Trash2,
  UploadCloud,
} from "lucide-react";
import { MapContainer, Marker, TileLayer, useMapEvents } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input, Label, Select, Textarea } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/feedback";
import { useToast } from "@/components/ui/toast";
import { incidentsApi, referenceDataApi, geocodeApi, type GeocodeResult } from "@/api/incidents";
import client, { normalizeError } from "@/api/client";
import { cn } from "@/lib/utils";
import { SEVERITY_LABELS, URGENCY_LABELS, type Severity, type Urgency } from "@/types";

const MUMBAI_CENTER: [number, number] = [19.076, 72.8777];

const STEPS = [
  "Category & title",
  "Description",
  "Location",
  "Severity",
  "Media",
  "Options",
  "Review",
] as const;

const pinIcon = L.divIcon({
  className: "",
  html: `<div style="width:22px;height:22px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);background:#dc2626;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,.4)"></div>`,
  iconSize: [22, 22],
  iconAnchor: [11, 22],
});

interface FormState {
  category_id: string;
  title: string;
  description: string;
  latitude: number | null;
  longitude: number | null;
  address_public: string;
  landmark: string;
  severity: Severity;
  urgency: Urgency;
  is_anonymous: boolean;
  files: File[];
}

function LocationPicker({
  position,
  onPick,
}: {
  position: [number, number] | null;
  onPick: (lat: number, lng: number) => void;
}) {
  useMapEvents({
    click(e) {
      onPick(e.latlng.lat, e.latlng.lng);
    },
  });
  return position ? <Marker position={position} icon={pinIcon} /> : null;
}

export function CreateIncidentPage() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [step, setStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [geoLoading, setGeoLoading] = useState(false);
  const [duplicateWarning, setDuplicateWarning] = useState<{
    has_duplicates: boolean;
    matches: Array<{ id: string; reference_number: string; title: string; distance_m: number }>;
  } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const duplicatesCheckedRef = useRef(false);

  const [form, setForm] = useState<FormState>({
    category_id: "",
    title: "",
    description: "",
    latitude: null,
    longitude: null,
    address_public: "",
    landmark: "",
    severity: "medium",
    urgency: "normal",
    is_anonymous: false,
    files: [],
  });

  const [addressSearch, setAddressSearch] = useState("");
  const [addressResults, setAddressResults] = useState<GeocodeResult[]>([]);
  const [addressLoading, setAddressLoading] = useState(false);
  const addressDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const { data: categories, isPending: categoriesLoading } = useQuery({
    queryKey: ["categories"],
    queryFn: referenceDataApi.categories,
  });

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const useMyLocation = useCallback(() => {
    if (!navigator.geolocation) {
      toast({ title: "Geolocation not supported on this device", variant: "error" });
      return;
    }
    setGeoLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        set("latitude", Number(pos.coords.latitude.toFixed(6)));
        set("longitude", Number(pos.coords.longitude.toFixed(6)));
        setGeoLoading(false);
        toast({ title: "Location captured", variant: "success" });
      },
      () => {
        setGeoLoading(false);
        toast({
          title: "Could not get your location",
          description: "Tap the map to place the pin manually.",
          variant: "error",
        });
      },
      { enableHighAccuracy: true, timeout: 10_000 },
    );
  }, [toast]);

  const handleAddressSearch = useCallback((value: string) => {
    setAddressSearch(value);
    if (addressDebounceRef.current) clearTimeout(addressDebounceRef.current);
    if (!value.trim()) {
      setAddressResults([]);
      return;
    }
    addressDebounceRef.current = setTimeout(async () => {
      setAddressLoading(true);
      try {
        const results = await geocodeApi.search(value, 5);
        setAddressResults(results);
      } catch {
        setAddressResults([]);
      } finally {
        setAddressLoading(false);
      }
    }, 300);
  }, []);

  const selectAddress = useCallback((result: GeocodeResult) => {
    set("latitude", result.lat);
    set("longitude", result.lon);
    set("address_public", result.display_name);
    setAddressSearch(result.display_name);
    setAddressResults([]);
  }, [set]);

  // Duplicate check when location + category are both set (once per session)
  useEffect(() => {
    const run = async () => {
      if (
        duplicatesCheckedRef.current ||
        !form.latitude ||
        !form.longitude ||
        !form.category_id
      ) {
        return;
      }
      duplicatesCheckedRef.current = true;
      try {
        const result = await incidentsApi.duplicatesCheck({
          latitude: form.latitude,
          longitude: form.longitude,
          category_id: form.category_id,
        });
        if (result.has_duplicates) setDuplicateWarning(result);
      } catch {
        /* duplicate check is advisory; submission does not depend on it */
      }
    };
    void run();
  }, [form.latitude, form.longitude, form.category_id]);

  const stepValid = (): boolean => {
    switch (step) {
      case 0:
        return !!form.category_id && form.title.trim().length >= 8;
      case 1:
        return form.description.trim().length >= 20;
      case 2:
        return form.latitude !== null && form.longitude !== null;
      case 3:
        return !!form.severity;
      default:
        return true;
    }
  };

  const addFiles = (list: FileList | null) => {
    if (!list) return;
    const valid: File[] = [];
    for (const file of Array.from(list)) {
      const isImage = file.type.startsWith("image/");
      const isVideo = file.type.startsWith("video/");
      const isPdf = file.type === "application/pdf";
      const tooBig =
        (isImage && file.size > 10 * 1024 * 1024) ||
        (isVideo && file.size > 100 * 1024 * 1024) ||
        (isPdf && file.size > 5 * 1024 * 1024);
      if (!isImage && !isVideo && !isPdf) {
        toast({ title: `${file.name}: unsupported type`, variant: "error" });
      } else if (tooBig) {
        toast({ title: `${file.name}: too large`, variant: "error" });
      } else {
        valid.push(file);
      }
    }
    set("files", [...form.files, ...valid].slice(0, 6));
  };

  const submit = async () => {
    setSubmitting(true);
    try {
      const incident = await incidentsApi.create({
        title: form.title.trim(),
        description: form.description.trim(),
        category_id: form.category_id,
        severity: form.severity,
        urgency: form.urgency,
        latitude: form.latitude,
        longitude: form.longitude,
        address_public: form.address_public,
        landmark: form.landmark,
        is_anonymous: form.is_anonymous,
      });
      const failedUploads: string[] = [];
      for (const file of form.files) {
        const data = new FormData();
        data.append("incident", incident.id);
        data.append("file", file);
        try {
          await client.post("/incidents/media/", data, {
            headers: { "Content-Type": "multipart/form-data" },
          });
        } catch {
          failedUploads.push(file.name);
        }
      }
      if (failedUploads.length > 0) {
        toast({
          title: `Reported: ${incident.reference_number}`,
          description: `${failedUploads.length} attachment(s) could not be uploaded. The report was still submitted.`,
          variant: "info",
        });
      } else {
        toast({
          title: `Reported: ${incident.reference_number}`,
          description: "Save this reference number to track progress.",
          variant: "success",
        });
      }
      navigate(`/incidents/${incident.id}`);
    } catch (error) {
      const normalized = normalizeError(error);
      const firstField = Object.values(normalized.fieldErrors)[0]?.[0];
      toast({
        title: "Submission failed",
        description: firstField ?? normalized.detail,
        variant: "error",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Report an incident</h1>
        <p className="text-sm text-muted-foreground">
          Step {step + 1} of {STEPS.length} — {STEPS[step]}
        </p>
      </div>

      {/* Progress */}
      <div className="flex gap-1" aria-hidden>
        {STEPS.map((label, index) => (
          <div
            key={label}
            className={cn(
              "h-1.5 flex-1 rounded-full",
              index <= step ? "bg-primary" : "bg-muted",
            )}
          />
        ))}
      </div>

      <Card>
        <CardContent className="p-6">
          {step === 0 && (
            <div className="space-y-4">
              {categoriesLoading ? (
                <Skeleton className="h-10 w-full" />
              ) : (
                <div className="space-y-2">
                  <Label htmlFor="category">What kind of problem is it?</Label>
                  <Select
                    id="category"
                    value={form.category_id}
                    onChange={(e) => {
                      set("category_id", e.target.value);
                      duplicatesCheckedRef.current = false;
                    }}
                  >
                    <option value="">Select a category…</option>
                    {categories?.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                        {c.is_emergency_category ? " ⚠" : ""}
                      </option>
                    ))}
                  </Select>
                </div>
              )}
              <div className="space-y-2">
                <Label htmlFor="title">Short title</Label>
                <Input
                  id="title"
                  placeholder="e.g. Deep pothole near the bus stop"
                  value={form.title}
                  onChange={(e) => set("title", e.target.value)}
                  maxLength={160}
                />
                <p className="text-xs text-muted-foreground">
                  {form.title.length}/160 (minimum 8 characters)
                </p>
              </div>
            </div>
          )}

          {step === 1 && (
            <div className="space-y-2">
              <Label htmlFor="description">Describe the problem</Label>
              <Textarea
                id="description"
                rows={6}
                placeholder="What is happening? How long has it been going on? Who is affected?"
                value={form.description}
                onChange={(e) => set("description", e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                {form.description.length} characters (minimum 20). Don't include personal
                contact details — staff will use your account information.
              </p>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <div className="relative">
                <Label htmlFor="address-search">Search for a place</Label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" aria-hidden />
                  <Input
                    id="address-search"
                    placeholder="e.g. Shivaji Park, Bandra, Mumbai"
                    value={addressSearch}
                    onChange={(e) => handleAddressSearch(e.target.value)}
                    className="pl-10"
                  />
                </div>
                {addressLoading && <p className="text-xs text-muted-foreground mt-1">Searching…</p>}
                {addressResults.length > 0 && (
                  <ul className="absolute z-10 mt-1 w-full rounded-md border bg-popover p-1 shadow-lg max-h-60 overflow-auto">
                    {addressResults.map((r) => (
                      <li
                        key={r.place_id}
                        onClick={() => selectAddress(r)}
                        className="px-3 py-2 text-sm hover:bg-accent cursor-pointer"
                      >
                        <p className="font-medium">{r.display_name}</p>
                        <p className="text-xs text-muted-foreground">
                          {r.address?.road || r.address?.suburb || r.address?.city || ""}
                        </p>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" onClick={useMyLocation} disabled={geoLoading}>
                  <Crosshair className="h-4 w-4" />
                  {geoLoading ? "Locating…" : "Use my location"}
                </Button>
                <span className="flex items-center gap-1 text-sm text-muted-foreground">
                  <MapPin className="h-4 w-4" />
                  {form.latitude
                    ? `${form.latitude}, ${form.longitude}`
                    : "Tap the map to drop a pin"}
                </span>
              </div>
              <div className="h-72 overflow-hidden rounded-lg border">
                <MapContainer center={form.latitude && form.longitude ? [form.latitude, form.longitude] : MUMBAI_CENTER} zoom={form.latitude ? 16 : 12} className="h-full w-full">
                  <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />
                  <LocationPicker
                    position={
                      form.latitude !== null && form.longitude !== null
                        ? [form.latitude, form.longitude]
                        : null
                    }
                    onPick={(lat, lng) => {
                      set("latitude", Number(lat.toFixed(6)));
                      set("longitude", Number(lng.toFixed(6)));
                    }}
                  />
                </MapContainer>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="address">Address (public)</Label>
                  <Input
                    id="address"
                    placeholder="e.g. Near Shivaji Park gate 2"
                    value={form.address_public}
                    onChange={(e) => set("address_public", e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="landmark">Landmark</Label>
                  <Input
                    id="landmark"
                    placeholder="e.g. opposite the temple"
                    value={form.landmark}
                    onChange={(e) => set("landmark", e.target.value)}
                  />
                </div>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>How severe is the problem?</Label>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {(Object.entries(SEVERITY_LABELS) as [Severity, string][]).map(
                    ([value, label]) => (
                      <button
                        key={value}
                        type="button"
                        onClick={() => set("severity", value)}
                        className={cn(
                          "rounded-md border p-3 text-sm font-medium transition-colors",
                          form.severity === value
                            ? "border-primary bg-primary/10 text-primary"
                            : "hover:bg-accent",
                        )}
                        aria-pressed={form.severity === value}
                      >
                        {label}
                      </button>
                    ),
                  )}
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="urgency">How urgent is it for you?</Label>
                <Select
                  id="urgency"
                  value={form.urgency}
                  onChange={(e) => set("urgency", e.target.value as Urgency)}
                >
                  {(Object.entries(URGENCY_LABELS) as [Urgency, string][]).map(
                    ([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ),
                  )}
                </Select>
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="space-y-4">
              <div
                className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 text-center"
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  addFiles(e.dataTransfer.files);
                }}
              >
                <UploadCloud className="mb-2 h-10 w-10 text-muted-foreground" aria-hidden />
                <p className="text-sm font-medium">Drag & drop photos or video</p>
                <p className="text-xs text-muted-foreground">
                  JPG/PNG/WebP up to 10 MB · MP4/WebM up to 100 MB · PDF up to 5 MB
                </p>
                <input
                  ref={fileInputRef}
                  type="file"
                  className="sr-only"
                  accept="image/jpeg,image/png,image/webp,video/mp4,video/webm,application/pdf"
                  capture="environment"
                  multiple
                  onChange={(e) => addFiles(e.target.files)}
                />
                <Button variant="outline" size="sm" className="mt-3" onClick={() => fileInputRef.current?.click()}>
                  <Camera className="h-4 w-4" /> Choose files / take photo
                </Button>
              </div>
              {form.files.length > 0 && (
                <ul className="space-y-2">
                  {form.files.map((file, index) => (
                    <li
                      key={`${file.name}-${index}`}
                      className="flex items-center justify-between rounded-md border p-2 text-sm"
                    >
                      <span className="truncate">{file.name}</span>
                      <span className="flex items-center gap-2 text-xs text-muted-foreground">
                        {(file.size / 1024 / 1024).toFixed(1)} MB
                        <button
                          type="button"
                          aria-label={`Remove ${file.name}`}
                          onClick={() =>
                            set(
                              "files",
                              form.files.filter((_, i) => i !== index),
                            )
                          }
                        >
                          <Trash2 className="h-4 w-4 text-danger" />
                        </button>
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {step === 5 && (
            <div className="space-y-3">
              <label className="flex items-start gap-3 text-sm">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={form.is_anonymous}
                  onChange={(e) => set("is_anonymous", e.target.checked)}
                />
                <span>
                  <span className="font-medium">Submit anonymously</span>
                  <span className="block text-muted-foreground">
                    Your name will not appear on the public report. (You'll still be able to
                    track it from your account.)
                  </span>
                </span>
              </label>
              <p className="rounded-md bg-muted p-3 text-xs text-muted-foreground">
                By submitting you confirm the information is accurate. False reports may be
                rejected by moderators. Your contact details are never shown publicly.
              </p>
            </div>
          )}

          {step === 6 && (
            <div className="space-y-3 text-sm">
              {duplicateWarning?.has_duplicates && (
                <div className="rounded-md border border-warning/50 bg-warning/10 p-3">
                  <p className="flex items-center gap-2 font-medium text-warning">
                    <AlertTriangle className="h-4 w-4" /> Possible duplicates found
                  </p>
                  <ul className="mt-2 space-y-1 text-xs">
                    {duplicateWarning.matches.map((m) => (
                      <li key={m.id}>
                        {m.reference_number} — {m.title} ({m.distance_m} m away)
                      </li>
                    ))}
                  </ul>
                  <p className="mt-2 text-xs text-muted-foreground">
                    If this is the same issue, consider not submitting — duplicate reports slow
                    response. You can still submit if it's genuinely different.
                  </p>
                </div>
              )}
              <dl className="grid gap-2 rounded-md border p-4">
                {[
                  ["Category", categories?.find((c) => c.id === form.category_id)?.name],
                  ["Title", form.title],
                  ["Description", form.description],
                  ["Location", form.latitude ? `${form.latitude}, ${form.longitude}` : "—"],
                  ["Address", form.address_public || "—"],
                  ["Severity", SEVERITY_LABELS[form.severity]],
                  ["Urgency", URGENCY_LABELS[form.urgency]],
                  ["Media", `${form.files.length} file(s)`],
                  ["Anonymous", form.is_anonymous ? "Yes" : "No"],
                ].map(([label, value]) => (
                  <div key={label} className="grid grid-cols-3 gap-2">
                    <dt className="font-medium text-muted-foreground">{label}</dt>
                    <dd className="col-span-2 line-clamp-2">{value}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )}

          {/* Navigation */}
          <div className="mt-6 flex items-center justify-between">
            <Button
              variant="outline"
              onClick={() => setStep((s) => Math.max(0, s - 1))}
              disabled={step === 0 || submitting}
            >
              <ChevronLeft className="h-4 w-4" /> Back
            </Button>
            {step < STEPS.length - 1 ? (
              <Button onClick={() => setStep((s) => s + 1)} disabled={!stepValid()}>
                Continue <ChevronRight className="h-4 w-4" />
              </Button>
            ) : (
              <Button variant="success" onClick={submit} disabled={submitting}>
                <Check className="h-4 w-4" />
                {submitting ? "Submitting…" : "Submit report"}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
