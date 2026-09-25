import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip as ChartTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatCard, Skeleton, ErrorState } from "@/components/ui/feedback";
import { Select } from "@/components/ui/input";
import { StatusBadge, SeverityBadge } from "@/components/incident/Badges";
import { analyticsApi, incidentsApi } from "@/api/incidents";
import { timeAgo } from "@/lib/utils";

export function AuthorityDashboard() {
  const [days, setDays] = useState(30);

  const { data: summary, isPending, isError, refetch } = useQuery({
    queryKey: ["analytics-summary", days],
    queryFn: () => analyticsApi.summary(days),
    refetchInterval: 60_000,
  });

  const { data: trends } = useQuery({
    queryKey: ["analytics-trends", days],
    queryFn: () => analyticsApi.trends(days),
  });

  const { data: byCategory } = useQuery({
    queryKey: ["analytics-by-category", days],
    queryFn: () => analyticsApi.byDimension("category", days),
  });

  const { data: critical } = useQuery({
    queryKey: ["critical-queue"],
    queryFn: () =>
      incidentsApi.list({ severity: "critical", status: ["submitted", "under_review", "assigned", "in_progress", "escalated"], page_size: 5 }),
    refetchInterval: 30_000,
  });

  const { data: recent } = useQuery({
    queryKey: ["recent-incidents"],
    queryFn: () => incidentsApi.list({ page_size: 6, ordering: "-created_at" }),
  });

  if (isError) return <ErrorState message="Could not load the dashboard." onRetry={refetch} />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Operations dashboard</h1>
          <p className="text-sm text-muted-foreground">
            City incident health at a glance. Auto-refreshes every minute.
          </p>
        </div>
        <Select
          aria-label="Date range"
          value={String(days)}
          onChange={(e) => setDays(Number(e.target.value))}
          className="w-40"
        >
          <option value="7">Last 7 days</option>
          <option value="30">Last 30 days</option>
          <option value="90">Last 90 days</option>
          <option value="365">Last year</option>
        </Select>
      </div>

      {/* KPI cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {isPending ? (
          Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-24 w-full" />)
        ) : summary ? (
          <>
            <StatCard label="Open incidents" value={summary.open} tone="warning" />
            <StatCard label="Awaiting verification" value={summary.awaiting_verification} />
            <StatCard label="High priority" value={summary.high_priority} tone="danger" />
            <StatCard label="Overdue (SLA)" value={summary.overdue} tone="danger" />
            <StatCard label="Emergency open" value={summary.emergency} tone="danger" />
            <StatCard
              label="Avg response"
              value={summary.avg_response_minutes !== null ? `${summary.avg_response_minutes}m` : "—"}
              tone="success"
            />
            <StatCard
              label="SLA compliance"
              value={summary.sla_compliance_pct !== null ? `${summary.sla_compliance_pct}%` : "—"}
              tone="success"
            />
            <StatCard
              label="Resolution rate"
              value={summary.resolution_rate_pct !== null ? `${summary.resolution_rate_pct}%` : "—"}
            />
          </>
        ) : null}
      </div>

      {/* Critical alert panel */}
      {critical && critical.results.length > 0 && (
        <Card className="border-danger/50 bg-danger/5">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base text-danger">
              <AlertTriangle className="h-5 w-5 animate-pulse-danger" aria-hidden />
              Critical incidents needing attention
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="divide-y">
              {critical.results.map((incident) => (
                <li key={incident.id}>
                  <Link
                    to={`/incidents/${incident.id}`}
                    className="flex items-center justify-between gap-3 py-2 text-sm hover:text-danger"
                  >
                    <span className="truncate font-medium">
                      {incident.reference_number} · {incident.title}
                    </span>
                    <span className="shrink-0 text-xs text-muted-foreground">
                      {timeAgo(incident.created_at)}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Trend chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Incidents over time</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={trends ?? []}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis
                  dataKey="date"
                  tickFormatter={(v: string) => v?.slice(5)}
                  fontSize={12}
                />
                <YAxis fontSize={12} allowDecimals={false} />
                <ChartTooltip />
                <Bar dataKey="total" fill="#1b6f8b" radius={[3, 3, 0, 0]} name="Submitted" />
                <Bar dataKey="resolved" fill="#16a34a" radius={[3, 3, 0, 0]} name="Resolved" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Category breakdown */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">By category</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={(byCategory ?? []).slice(0, 8)} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis type="number" fontSize={12} allowDecimals={false} />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={110}
                  fontSize={11}
                  tickFormatter={(v: string) => (v.length > 16 ? `${v.slice(0, 15)}…` : v)}
                />
                <ChartTooltip />
                <Bar dataKey="total" fill="#1b6f8b" radius={[0, 3, 3, 0]} name="Incidents" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Recent activity */}
      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle className="text-base">Latest submissions</CardTitle>
          <Link to="/queue" className="text-sm text-primary hover:underline">
            Open queue →
          </Link>
        </CardHeader>
        <CardContent className="p-0">
          <ul className="divide-y">
            {recent?.results.map((incident) => (
              <li key={incident.id}>
                <Link
                  to={`/incidents/${incident.id}`}
                  className="flex items-center justify-between gap-3 p-3 text-sm hover:bg-accent/50"
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium">{incident.title}</p>
                    <p className="text-xs text-muted-foreground">
                      {incident.reference_number} · {timeAgo(incident.created_at)}
                    </p>
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <SeverityBadge severity={incident.severity} />
                    <StatusBadge status={incident.status} />
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
