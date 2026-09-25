import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Search, Download, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/feedback";
import { StatusBadge, SeverityBadge } from "@/components/incident/Badges";
import { incidentsApi, exportIncidentCsv, type IncidentFilters } from "@/api/incidents";
import { STATUS_LABELS } from "@/types";
import { timeAgo } from "@/lib/utils";

export function MyIncidentsPage() {
  const [filters, setFilters] = useState<IncidentFilters>({ page_size: 20 });
  const [q, setQ] = useState("");

  const { data, isPending, isError, refetch } = useQuery({
    queryKey: ["incidents", "mine", filters],
    queryFn: () => incidentsApi.list(filters),
  });

  const update = (patch: Partial<IncidentFilters>) =>
    setFilters((prev) => ({ ...prev, ...patch }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">My reports</h1>
        <p className="text-sm text-muted-foreground">
          Every incident you've reported, with live status.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <div className="relative flex-1 min-w-52">
          <Input
            placeholder="Search by title or reference…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && update({ q, page: 1 })}
            aria-label="Search reports"
          />
        </div>
        <Button variant="outline" onClick={() => update({ q, page: 1 })}>
          <Search className="h-4 w-4" /> Search
        </Button>
        <Button variant="outline" onClick={() => exportIncidentCsv(filters)}>
          <FileText className="h-4 w-4" /> Export CSV
        </Button>
        <Select
          aria-label="Filter by status"
          value={filters.status?.[0] ?? ""}
          onChange={(e) => update({ status: e.target.value ? [e.target.value] : undefined })}
          className="w-44"
        >
          <option value="">All statuses</option>
          {Object.entries(STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
      </div>

      {isPending && <Skeleton className="h-64 w-full" />}
      {isError && <ErrorState message="Could not load your reports." onRetry={refetch} />}

      {data && data.results.length === 0 && (
        <EmptyState title="No reports found" description="Try clearing filters." />
      )}

      {data && data.results.length > 0 && (
        <Card>
          <CardContent className="p-0">
            <ul className="divide-y">
              {data.results.map((incident) => (
                <li key={incident.id}>
                  <Link
                    to={`/incidents/${incident.id}`}
                    className="flex items-center justify-between gap-3 p-4 hover:bg-accent/50"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-medium">{incident.title}</p>
                      <p className="text-xs text-muted-foreground">
                        {incident.reference_number} · {incident.category?.name} ·{" "}
                        {timeAgo(incident.created_at)}
                      </p>
                    </div>
                    <div className="flex shrink-0 flex-wrap gap-2">
                      {incident.is_overdue && (
                        <span className="rounded-full bg-danger/15 px-2 py-0.5 text-xs font-semibold text-danger">
                          Overdue
                        </span>
                      )}
                      <SeverityBadge severity={incident.severity} />
                      <StatusBadge status={incident.status} />
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {data && data.count > (data.results?.length ?? 0) && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            Page {filters.page ?? 1} · {data.count} total
          </span>
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
    </div>
  );
}
