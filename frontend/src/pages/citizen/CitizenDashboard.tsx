import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { PlusCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatCard, EmptyState, Skeleton } from "@/components/ui/feedback";
import { StatusBadge, SeverityBadge } from "@/components/incident/Badges";
import { incidentsApi } from "@/api/incidents";
import { notificationsApi } from "@/api/auth";
import { timeAgo } from "@/lib/utils";

export function CitizenDashboard() {
  const { data: active, isPending } = useQuery({
    queryKey: ["incidents", "mine", "active"],
    queryFn: () =>
      incidentsApi.list({
        status: ["submitted", "under_review", "verified", "assigned", "in_progress", "reopened"],
        page_size: 5,
      }),
  });

  const { data: resolved } = useQuery({
    queryKey: ["incidents", "mine", "resolved"],
    queryFn: () => incidentsApi.list({ status: ["resolved", "closed"], page_size: 5 }),
  });

  const { data: notifications } = useQuery({
    queryKey: ["notifications"],
    queryFn: notificationsApi.list,
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Your dashboard</h1>
          <p className="text-sm text-muted-foreground">
            Track your reports and the city's response.
          </p>
        </div>
        <Link to="/report">
          <Button>
            <PlusCircle className="h-4 w-4" /> Report new incident
          </Button>
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Active reports" value={active?.count ?? 0} tone="warning" />
        <StatCard label="Resolved" value={resolved?.count ?? 0} tone="success" />
        <StatCard label="Unread notifications" value={notifications?.unread_count ?? 0} />
        <StatCard
          label="Response time (avg city)"
          value="—"
          hint="Visible on the authority dashboard"
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent active reports</CardTitle>
        </CardHeader>
        <CardContent>
          {isPending ? (
            <div className="space-y-2">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          ) : active && active.results.length > 0 ? (
            <ul className="divide-y">
              {active.results.map((incident) => (
                <li key={incident.id}>
                  <Link
                    to={`/incidents/${incident.id}`}
                    className="flex items-center justify-between gap-3 py-3 hover:text-primary"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-medium">{incident.title}</p>
                      <p className="text-xs text-muted-foreground">
                        {incident.reference_number} · updated {timeAgo(incident.updated_at)}
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
          ) : (
            <EmptyState
              title="No active reports"
              description="When you report an incident it will appear here with live status."
              action={
                <Link to="/report">
                  <Button size="sm">Report your first incident</Button>
                </Link>
              }
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
