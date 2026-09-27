import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckSquare, Download, Search, Square, Filter, X, ChevronDown, ChevronUp, MoreHorizontal, UserPlus, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/feedback";
import { StatusBadge, SeverityBadge } from "@/components/incident/Badges";
import { incidentsApi, referenceDataApi, type IncidentFilters } from "@/api/incidents";
import { usersApi } from "@/api/auth";
import { normalizeError } from "@/api/client";
import { useToast } from "@/components/ui/toast";
import { useAuthStore } from "@/store/auth";
import { STATUS_LABELS, SEVERITY_LABELS, type Incident, type Severity, type IncidentStatus, type User } from "@/types";
import { timeAgo } from "@/lib/utils";

function AssignDialog({
  incident,
  staff,
  staffPending,
  onPick,
  onAuto,
  onClose,
}: {
  incident: Incident;
  staff: User[] | undefined;
  staffPending: boolean;
  onPick: (id: string) => void;
  onAuto: () => void;
  onClose: () => void;
}) {
  const [search, setSearch] = useState("");
  const [dept, setDept] = useState("");

  const departments = useMemo(() => {
    const map = new Map<string, string>();
    (staff ?? []).forEach((m) => {
      if (m.department) map.set(m.department.id, m.department.name);
    });
    return [...map.entries()].sort((a, b) => a[1].localeCompare(b[1]));
  }, [staff]);

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return (staff ?? []).filter((m) => {
      if (dept && m.department?.id !== dept) return false;
      if (!needle) return true;
      return `${m.first_name} ${m.last_name} ${m.email}`.toLowerCase().includes(needle);
    });
  }, [staff, search, dept]);

  const grouped = useMemo(() => {
    const groups = new Map<string, { name: string; members: User[] }>();
    filtered.forEach((m) => {
      const key = m.department?.id ?? "none";
      const name = m.department?.name ?? "No department";
      if (!groups.has(key)) groups.set(key, { name, members: [] });
      groups.get(key)!.members.push(m);
    });
    return [...groups.values()].sort((a, b) => a.name.localeCompare(b.name));
  }, [filtered]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-label={`Assign ${incident.reference_number}`}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <Card className="w-full max-w-lg">
        <CardContent className="p-6">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h2 className="font-semibold">Assign {incident.reference_number}</h2>
              <p className="mt-1 truncate text-sm text-muted-foreground">{incident.title}</p>
            </div>
            <Button size="sm" variant="outline" onClick={onAuto} title="Assign by workload">
              Auto
            </Button>
          </div>

          <div className="mt-4 grid gap-2 sm:grid-cols-[1fr_180px]">
            <Input
              placeholder="Search name or email…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              aria-label="Search staff"
            />
            <Select
              value={dept}
              onChange={(e) => setDept(e.target.value)}
              aria-label="Filter by department"
            >
              <option value="">All departments</option>
              {departments.map(([id, name]) => (
                <option key={id} value={id}>
                  {name}
                </option>
              ))}
            </Select>
          </div>

          <div className="mt-3 max-h-80 overflow-y-auto rounded-md border">
            {staffPending ? (
              <Skeleton className="m-3 h-16" />
            ) : grouped.length === 0 ? (
              <p className="p-4 text-sm text-muted-foreground">
                {staff?.length
                  ? "No staff match these filters."
                  : "No staff visible. Ask an administrator to add department members."}
              </p>
            ) : (
              grouped.map((group) => (
                <div key={group.name}>
                  <p className="sticky top-0 bg-muted/80 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground backdrop-blur">
                    {group.name} · {group.members.length}
                  </p>
                  {group.members.map((member) => (
                    <button
                      key={member.id}
                      className="flex w-full items-center justify-between gap-3 border-t px-3 py-2.5 text-left text-sm hover:bg-accent"
                      onClick={() => onPick(member.id)}
                    >
                      <span className="min-w-0">
                        <span className="block truncate font-medium">
                          {member.first_name} {member.last_name}
                        </span>
                        <span className="block truncate text-xs text-muted-foreground">
                          {member.role.replace("_", " ")} · {member.email}
                        </span>
                      </span>
                      {member.is_locked && (
                        <span className="shrink-0 rounded-full bg-warning/15 px-2 py-0.5 text-[11px] font-medium text-warning">
                          locked
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              ))
            )}
          </div>

          <div className="mt-3 flex items-center justify-between gap-2">
            <p className="text-xs text-muted-foreground">
              {filtered.length} of {staff?.length ?? 0} shown
            </p>
            <Button variant="ghost" size="sm" onClick={onClose}>
              Cancel
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export function IncidentQueuePage() {
  const [searchParams] = useSearchParams();
  const initialStatus = searchParams.get("status");
  const [filters, setFilters] = useState<IncidentFilters>({
    page_size: 25,
    status: initialStatus ? [initialStatus] : undefined,
  });
  const [q, setQ] = useState("");
  const [assigning, setAssigning] = useState<Incident | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [reviewNote, setReviewNote] = useState("Verified after review");
  const user = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [showFilters, setShowFilters] = useState(true);

  const { data, isPending, isError, refetch } = useQuery({
    queryKey: ["queue", filters],
    queryFn: () => incidentsApi.list(filters),
  });

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: referenceDataApi.categories,
  });

  const { data: staff, isPending: staffPending } = useQuery({
    queryKey: ["staff"],
    queryFn: () => usersApi.staff(undefined, ["department_staff", "emergency_responder", "volunteer"]),
    enabled: assigning !== null,
  });

  const update = (patch: Partial<IncidentFilters>) =>
    setFilters((prev) => ({ ...prev, ...patch, page: 1 }));

  const canAssign =
    user?.role === "department_staff" || user?.role === "city_admin" || user?.role === "superuser";
  const isAdmin = user?.role === "city_admin" || user?.role === "superuser";
  // submitted → verified is admin-only; staff verify from under_review.
  const canVerify = (incident: Incident) =>
    isAdmin || (user?.role === "department_staff" && incident.status === "under_review");

  const visibleIds = data?.results.map((incident) => incident.id) ?? [];
  const selectedIncidents = data?.results.filter((incident) => selectedIds.includes(incident.id)) ?? [];
  const allVisibleSelected = visibleIds.length > 0 && visibleIds.every((id) => selectedIds.includes(id));

  const toggleAllVisible = () => {
    setSelectedIds((current) =>
      allVisibleSelected
        ? current.filter((id) => !visibleIds.includes(id))
        : Array.from(new Set([...current, ...visibleIds])),
    );
  };

  const toggleSelected = (id: string) => {
    setSelectedIds((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    );
  };

  const verify = async (incident: Incident, to: IncidentStatus, note = reviewNote) => {
    try {
      await incidentsApi.changeStatus(incident.id, to, note);
      toast({
        title: to === "verified" ? "Incident verified" : "Incident rejected",
        variant: to === "verified" ? "success" : "info",
      });
      queryClient.invalidateQueries({ queryKey: ["queue"] });
    } catch (error) {
      toast({ title: "Action failed", description: normalizeError(error).detail, variant: "error" });
    }
  };

  const bulkStatus = async (to: IncidentStatus) => {
    const candidates = selectedIncidents.filter((incident) =>
      to === "under_review"
        ? incident.status === "submitted"
        : incident.status === "submitted" || incident.status === "under_review",
    );
    if (candidates.length === 0) {
      toast({ title: "No selected incidents can use that action", variant: "info" });
      return;
    }
    const failures: string[] = [];
    for (const incident of candidates) {
      try {
        await incidentsApi.changeStatus(
          incident.id,
          to,
          to === "rejected" ? reviewNote || "Rejected after review" : reviewNote,
        );
      } catch {
        failures.push(incident.reference_number);
      }
    }
    setSelectedIds((current) => current.filter((id) => !candidates.some((i) => i.id === id)));
    queryClient.invalidateQueries({ queryKey: ["queue"] });
    toast({
      title: failures.length ? "Bulk action completed with errors" : "Bulk action completed",
      description: failures.length ? `Failed: ${failures.join(", ")}` : `${candidates.length} incident(s) updated.`,
      variant: failures.length ? "error" : "success",
    });
  };

  const bulkAutoAssign = async () => {
    const candidates = selectedIncidents.filter((incident) => !incident.assigned_staff_name);
    if (candidates.length === 0) {
      toast({ title: "No selected incidents need assignment", variant: "info" });
      return;
    }
    const failures: string[] = [];
    for (const incident of candidates) {
      try {
        await incidentsApi.assign(incident.id, { auto: true, note: reviewNote });
      } catch {
        failures.push(incident.reference_number);
      }
    }
    setSelectedIds((current) => current.filter((id) => !candidates.some((i) => i.id === id)));
    queryClient.invalidateQueries({ queryKey: ["queue"] });
    toast({
      title: failures.length ? "Auto-assignment completed with errors" : "Auto-assignment completed",
      description: failures.length ? `Failed: ${failures.join(", ")}` : `${candidates.length} incident(s) assigned.`,
      variant: failures.length ? "error" : "success",
    });
  };

  const autoAssign = async (incident: Incident) => {
    try {
      await incidentsApi.assign(incident.id, { auto: true });
      toast({ title: "Incident auto-assigned", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["queue"] });
    } catch (error) {
      toast({ title: "Assignment failed", description: normalizeError(error).detail, variant: "error" });
    }
  };

  const manualAssign = async (staffId: string) => {
    if (!assigning) return;
    try {
      await incidentsApi.assign(assigning.id, { assignee_id: staffId });
      toast({ title: "Assigned successfully", variant: "success" });
      queryClient.invalidateQueries({ queryKey: ["queue"] });
    } catch (error) {
      toast({ title: "Assignment failed", description: normalizeError(error).detail, variant: "error" });
    } finally {
      setAssigning(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Incident queue</h1>
          <p className="text-sm text-muted-foreground">
            Verify, approve, reject and assign incidents scoped to your role.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => setShowFilters(!showFilters)} className="flex items-center gap-2">
            <Filter className="h-4 w-4" />
            Filters
            {showFilters ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
          <Button variant="outline" onClick={() => incidentsApi.exportIncidentCsv(filters)}>
            <Download className="h-4 w-4" /> Export CSV
          </Button>
        </div>
      </div>

      {/* Collapsible Filters */}
      {showFilters && (
        <Card className="animate-slide-down">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Filters</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
              <div className="space-y-1.5">
                <label className="text-sm font-medium" htmlFor="queue-search">Search</label>
                <div className="flex gap-1">
                  <Input
                    id="queue-search"
                    className="flex-1"
                    placeholder="Search reference/title…"
                    value={q}
                    onChange={(e) => setQ(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && update({ q })}
                    aria-label="Search incidents"
                  />
                  <Button variant="outline" onClick={() => update({ q })}>
                    <Search className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium" htmlFor="queue-status">Status</label>
                <Select
                  id="queue-status"
                  aria-label="Status filter"
                  value={filters.status?.[0] ?? ""}
                  onChange={(e) => update({ status: e.target.value ? [e.target.value] : undefined })}
                  className="w-full"
                >
                  <option value="">All statuses</option>
                  {Object.entries(STATUS_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </Select>
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium" htmlFor="queue-severity">Severity</label>
                <Select
                  id="queue-severity"
                  aria-label="Severity filter"
                  value={filters.severity ?? ""}
                  onChange={(e) => update({ severity: e.target.value || undefined })}
                  className="w-full"
                >
                  <option value="">All severity</option>
                  {Object.entries(SEVERITY_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </Select>
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium" htmlFor="queue-category">Category</label>
                <Select
                  id="queue-category"
                  aria-label="Category filter"
                  value={filters.category ?? ""}
                  onChange={(e) => update({ category: e.target.value || undefined })}
                  className="w-full"
                >
                  <option value="">All categories</option>
                  {categories?.map((c) => (
                    <option key={c.id} value={c.slug}>
                      {c.name}
                    </option>
                  ))}
                </Select>
              </div>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-2 lg:grid-cols-4">
              <div className="space-y-1.5">
                <label className="text-sm font-medium" htmlFor="queue-sla">SLA State</label>
                <Select
                  id="queue-sla"
                  aria-label="SLA filter"
                  value={filters.sla_state ?? ""}
                  onChange={(e) => update({ sla_state: e.target.value || undefined })}
                  className="w-full"
                >
                  <option value="">All SLA states</option>
                  <option value="breached">Breached</option>
                  <option value="active">Active</option>
                  <option value="met">Met</option>
                </Select>
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium" htmlFor="queue-review-note">Review Note</label>
                <Select
                  id="queue-review-note"
                  aria-label="Review note template"
                  value={reviewNote}
                  onChange={(e) => setReviewNote(e.target.value)}
                  className="w-full"
                >
                  <option value="Verified after review">Verified after review</option>
                  <option value="Evidence and location look valid">Evidence and location look valid</option>
                  <option value="Duplicate or insufficient evidence">Duplicate or insufficient evidence</option>
                  <option value="Rejected after department review">Rejected after department review</option>
                </Select>
              </div>
              <div className="space-y-1.5 md:col-span-2 lg:col-span-2">
                <label className="text-sm font-medium">Quick Actions</label>
                <div className="flex flex-wrap gap-2">
                  <Button variant="outline" size="sm" onClick={() => {
                    setQ("");
                    update({ status: undefined, severity: undefined, category: undefined, sla_state: undefined, q: "" });
                  }}>
                    <X className="h-4 w-4" /> Clear All Filters
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => void refetch()}>
                    <MoreHorizontal className="h-4 w-4" /> Refresh
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {selectedIds.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-card p-3">
          <p className="text-sm font-medium">{selectedIds.length} selected</p>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" onClick={() => bulkStatus("under_review")}>
              Start review
            </Button>
            <Button size="sm" variant="success" onClick={() => bulkStatus("verified")}>
              Verify selected
            </Button>
            <Button size="sm" variant="danger" onClick={() => bulkStatus("rejected")}>
              Reject selected
            </Button>
            {canAssign && (
              <Button size="sm" variant="outline" onClick={bulkAutoAssign}>
                Auto-assign
              </Button>
            )}
            <Button size="sm" variant="ghost" onClick={() => setSelectedIds([])}>
              Clear
            </Button>
          </div>
        </div>
      )}

      {isPending && <Skeleton className="h-72 w-full" />}
      {isError && <ErrorState message="Could not load the queue." onRetry={refetch} />}
      {data?.results.length === 0 && (
        <EmptyState title="No incidents match these filters" />
      )}

      {data && data.results.length > 0 && (
        <Card>
          <CardContent className="overflow-x-auto p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50 text-left">
                  <th className="w-10 p-3">
                    <button type="button" onClick={toggleAllVisible} aria-label="Select all visible incidents">
                      {allVisibleSelected ? <CheckSquare className="h-4 w-4" /> : <Square className="h-4 w-4" />}
                    </button>
                  </th>
                  <th className="p-3 font-medium">Reference</th>
                  <th className="p-3 font-medium">Title</th>
                  <th className="p-3 font-medium">Status</th>
                  <th className="p-3 font-medium">Severity</th>
                  <th className="p-3 font-medium">Assigned</th>
                  <th className="p-3 font-medium">Age</th>
                  <th className="p-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((incident) => (
                  <tr key={incident.id} className="border-b hover:bg-accent/40">
                    <td className="p-3">
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(incident.id)}
                        onChange={() => toggleSelected(incident.id)}
                        aria-label={`Select ${incident.reference_number}`}
                      />
                    </td>
                    <td className="p-3 font-mono text-xs">{incident.reference_number}</td>
                    <td className="max-w-64 truncate p-3">
                      <Link to={`/incidents/${incident.id}`} className="font-medium hover:text-primary">
                        {incident.title}
                      </Link>
                      <p className="text-xs text-muted-foreground">{incident.category?.name}</p>
                    </td>
                    <td className="p-3">
                      <StatusBadge status={incident.status as IncidentStatus} />
                    </td>
                    <td className="p-3">
                      <SeverityBadge severity={incident.severity as Severity} critical={incident.is_emergency} />
                    </td>
                    <td className="p-3 text-xs">
                      {incident.assigned_staff_name ?? <span className="text-warning">Unassigned</span>}
                    </td>
                    <td className="p-3 text-xs text-muted-foreground">{timeAgo(incident.created_at)}</td>
                    <td className="p-3">
                      <div className="flex flex-wrap gap-1">
                        {canVerify(incident) &&
                          (incident.status === "submitted" || incident.status === "under_review") && (
                            <>
                              {user?.role === "department_staff" && incident.status === "submitted" ? (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => verify(incident, "under_review")}
                                >
                                  Review
                                </Button>
                              ) : (
                                <>
                                  <Button
                                    size="sm"
                                    variant="success"
                                    onClick={() => verify(incident, "verified")}
                                  >
                                    Verify
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="danger"
                                    onClick={() => verify(incident, "rejected")}
                                  >
                                    Reject
                                  </Button>
                                </>
                              )}
                            </>
                          )}
                        {canAssign && !incident.assigned_staff_name && (
                          <>
                            <Button size="sm" variant="outline" onClick={() => autoAssign(incident)} title="Auto-assign by workload">
                              <Zap className="h-3.5 w-3.5" /> Auto
                            </Button>
                            <Button size="sm" variant="secondary" onClick={() => setAssigning(incident)} title="Pick a staff member">
                              <UserPlus className="h-3.5 w-3.5" /> Assign
                            </Button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      {/* Pagination */}
      {data && data.count > data.results.length && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">{data.count} incidents</span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={!data.previous}
              onClick={() => update({ page: Math.max(1, (filters.page ?? 1) - 1) })}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!data.next}
              onClick={() => update({ page: (filters.page ?? 1) + 1 })}
            >
              Next
            </Button>
          </div>
        </div>
      )}

      {/* Assign dialog — searchable, grouped by department, scrollable */}
      {assigning && (
        <AssignDialog
          incident={assigning}
          staff={staff}
          staffPending={staffPending}
          onPick={manualAssign}
          onAuto={() => {
            const target = assigning;
            setAssigning(null);
            void autoAssign(target);
          }}
          onClose={() => setAssigning(null)}
        />
      )}
    </div>
  );
}
