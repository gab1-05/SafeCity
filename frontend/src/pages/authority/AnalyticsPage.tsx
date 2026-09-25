import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip as ChartTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/input";
import { StatCard, Skeleton, ErrorState } from "@/components/ui/feedback";
import { analyticsApi, incidentsApi } from "@/api/incidents";

export function AnalyticsPage() {
  const [days, setDays] = useState(30);

  const { data: summary, isPending, isError, refetch } = useQuery({
    queryKey: ["analytics-summary", days],
    queryFn: () => analyticsApi.summary(days),
  });

  const { data: trends } = useQuery({
    queryKey: ["analytics-trends", days],
    queryFn: () => analyticsApi.trends(days),
  });

  const { data: byWard } = useQuery({
    queryKey: ["analytics-by-ward", days],
    queryFn: () => analyticsApi.byDimension("ward", days),
  });

  const { data: byDept } = useQuery({
    queryKey: ["analytics-by-department", days],
    queryFn: () => analyticsApi.byDimension("department", days),
  });

  const { data: byStatus } = useQuery({
    queryKey: ["analytics-by-status", days],
    queryFn: () => analyticsApi.byDimension("status", days),
  });

  if (isError) return <ErrorState message="Could not load analytics." onRetry={refetch} />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Analytics & reports</h1>
          <p className="text-sm text-muted-foreground">
            Incident trends, performance and SLA compliance.
          </p>
        </div>
        <div className="flex gap-2">
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
          <Button variant="outline" onClick={() => incidentsApi.exportCsv()}>
            <Download className="h-4 w-4" /> CSV
          </Button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {isPending ? (
          Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-24 w-full" />)
        ) : summary ? (
          <>
            <StatCard label="Total in window" value={summary.in_window} />
            <StatCard label="Reopened" value={summary.reopened_in_window} tone="warning" />
            <StatCard label="Duplicates detected" value={summary.duplicates_in_window} />
            <StatCard
              label="Avg satisfaction"
              value={summary.avg_satisfaction ?? "—"}
              tone="success"
            />
            <StatCard
              label="Avg resolution"
              value={
                summary.avg_resolution_minutes !== null
                  ? `${Math.round(summary.avg_resolution_minutes / 60)}h`
                  : "—"
              }
            />
            <StatCard
              label="SLA compliance"
              value={summary.sla_compliance_pct !== null ? `${summary.sla_compliance_pct}%` : "—"}
              tone={summary.sla_compliance_pct !== null && summary.sla_compliance_pct < 80 ? "danger" : "success"}
            />
            <StatCard label="Resolved" value={summary.resolved_in_window} tone="success" />
            <StatCard label="Emergency open" value={summary.emergency} tone="danger" />
          </>
        ) : null}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Submitted vs resolved</CardTitle>
        </CardHeader>
        <CardContent className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={trends ?? []}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis dataKey="date" tickFormatter={(v: string) => v?.slice(5)} fontSize={12} />
              <YAxis fontSize={12} allowDecimals={false} />
              <ChartTooltip />
              <Legend />
              <Line type="monotone" dataKey="total" stroke="#1b6f8b" name="Submitted" strokeWidth={2} />
              <Line type="monotone" dataKey="resolved" stroke="#16a34a" name="Resolved" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Department performance</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={(byDept ?? []).slice(0, 8)} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis type="number" fontSize={12} allowDecimals={false} />
                <YAxis type="category" dataKey="name" width={130} fontSize={11} />
                <ChartTooltip />
                <Bar dataKey="resolved" fill="#16a34a" name="Resolved" radius={[0, 3, 3, 0]} />
                <Bar dataKey="sla_breached" fill="#dc2626" name="SLA breached" radius={[0, 3, 3, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Distribution by ward</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={(byWard ?? []).slice(0, 10)} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis type="number" fontSize={12} allowDecimals={false} />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={110}
                  fontSize={11}
                  tickFormatter={(v: string) => (v.length > 14 ? `${v.slice(0, 13)}…` : v)}
                />
                <ChartTooltip />
                <Bar dataKey="total" fill="#1b6f8b" name="Incidents" radius={[0, 3, 3, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Status distribution</CardTitle>
        </CardHeader>
        <CardContent className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={byStatus ?? []}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis dataKey="name" fontSize={11} />
              <YAxis fontSize={12} allowDecimals={false} />
              <ChartTooltip />
              <Bar dataKey="total" fill="#1b6f8b" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
}
