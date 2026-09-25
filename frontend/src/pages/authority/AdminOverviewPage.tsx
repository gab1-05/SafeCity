import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  BarChart3,
  Building2,
  CheckCircle2,
  FileClock,
  Megaphone,
  ScrollText,
  ShieldAlert,
  UserCog,
  Users,
  Bell,
  MapPin,
  Clock,
  TrendingUp,
  TrendingDown,
  UserPlus,
  UserCheck,
  UserX,
  Lock,
  Unlock,
  Activity,
  Eye,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ErrorState, Skeleton, StatCard } from "@/components/ui/feedback";
import client from "@/api/client";
import { useAuthStore } from "@/store/auth";
import { timeAgo } from "@/lib/utils";
import { STATUS_LABELS, type IncidentStatus } from "@/types";
import { cn } from "@/lib/utils";

interface AdminOverview {
  users: { 
    total: number; 
    citizens: number; 
    staff: number; 
    locked: number; 
    new_this_week: number;
    active_this_week: number;
    with_2fa: number;
  };
  incidents: {
    total: number;
    open: number;
    awaiting_verification: number;
    overdue: number;
    emergency: number;
    resolved_rate_pct: number | null;
    sla_compliance_pct: number | null;
    avg_satisfaction: number | null;
    status_breakdown: Array<{ status: IncidentStatus; count: number }>;
    by_category: Array<{ name: string; count: number }>;
    by_ward: Array<{ name: string; count: number }>;
  };
  departments: Array<{ id: string; name: string; open_incidents: number; staff_count: number }>;
  deletion_requests: Array<{ id: string; email: string; reason: string; requested_at: string }>;
  recent_audit: Array<{
    id: string;
    action: string;
    actor: string | null;
    created_at: string;
  }>;
  sla_breaches: Array<{ id: string; reference: string; title: string; department: string; overdue_hours: number }>;
}

export function AdminOverviewPage() {
  const user = useAuthStore((s) => s.user);
  const { data, isPending, isError, refetch } = useQuery({
    queryKey: ["admin-overview"],
    queryFn: async (): Promise<AdminOverview> => {
      const { data } = await client.get("/admin/overview/");
      return data;
    },
    refetchInterval: 60_000,
  });

  if (isError)
    return (
      <ErrorState message="Could not load the admin overview." onRetry={refetch} />
    );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Administration overview</h1>
        <p className="text-sm text-muted-foreground">
          Platform health, people and governance — {user?.role === "superuser" ? "superuser" : "city admin"} view. Auto-refreshes every minute.
        </p>
      </div>

      {/* KPI row 1 — incidents */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {isPending || !data ? (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24 w-full" />)
        ) : (
          <>
            <StatCard label="Open incidents" value={data.incidents.open} tone="warning" />
            <StatCard label="Awaiting verification" value={data.incidents.awaiting_verification} />
            <StatCard label="Overdue (SLA)" value={data.incidents.overdue} tone="danger" />
            <StatCard label="Emergency open" value={data.incidents.emergency} tone="danger" />
          </>
        )}
      </div>

      {/* KPI row 2 — people */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {isPending || !data ? (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24 w-full" />)
        ) : (
          <>
            <StatCard label="Total users" value={data.users.total} />
            <StatCard label="Citizens" value={data.users.citizens} tone="success" />
            <StatCard label="Staff accounts" value={data.users.staff} />
            <StatCard
              label="Locked accounts"
              value={data.users.locked}
              tone={data.users.locked > 0 ? "danger" : "success"}
            />
          </>
        )}
      </div>

      {/* KPI row 3 — engagement & security */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {isPending || !data ? (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24 w-full" />)
        ) : (
          <>
            <StatCard label="Active this week" value={data.users.active_this_week} tone="success" />
            <StatCard label="2FA enabled" value={data.users.with_2fa} tone="warning" />
            <StatCard label="New users (7d)" value={data.users.new_this_week} />
            <StatCard label="Locked accounts" value={data.users.locked} tone={data.users.locked > 0 ? "danger" : "success"} />
          </>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <CheckCircle2 className="h-4 w-4 text-success" aria-hidden /> Resolution quality
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isPending || !data ? (
              <Skeleton className="h-32 w-full" />
            ) : (
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-lg border p-3">
                  <p className="text-xs text-muted-foreground">Resolution rate</p>
                  <p className="mt-1 text-2xl font-bold">
                    {data.incidents.resolved_rate_pct ?? 0}%
                  </p>
                </div>
                <div className="rounded-lg border p-3">
                  <p className="text-xs text-muted-foreground">Avg satisfaction</p>
                  <p className="mt-1 text-2xl font-bold">
                    {data.incidents.avg_satisfaction
                      ? data.incidents.avg_satisfaction.toFixed(1)
                      : "—"}
                  </p>
                </div>
                <div className="rounded-lg border p-3">
                  <p className="text-xs text-muted-foreground">New users this week</p>
                  <p className="mt-1 text-2xl font-bold">{data.users.new_this_week}</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ShieldAlert className="h-4 w-4 text-warning" aria-hidden /> Incident status mix
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isPending || !data ? (
              <Skeleton className="h-32 w-full" />
            ) : (
              <ul className="grid gap-2 sm:grid-cols-2">
                {data.incidents.status_breakdown.map((row) => (
                  <li key={row.status} className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
                    <span>{STATUS_LABELS[row.status] ?? row.status}</span>
                    <span className="font-semibold tabular-nums">{row.count}</span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Department load */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Building2 className="h-4 w-4 text-primary" aria-hidden /> Department load (open)
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isPending || !data ? (
              <Skeleton className="h-40 w-full" />
            ) : (
              <ul className="space-y-2">
                {data.departments.map((d) => {
                  const max = Math.max(...data.departments.map((x) => x.open_incidents), 1);
                  const staffPct = d.staff_count > 0 ? Math.min(100, (d.open_incidents / d.staff_count) * 20) : 0;
                  return (
                    <li key={d.id} className="flex items-center gap-3 text-sm">
                      <span className="w-44 shrink-0 truncate">{d.name}</span>
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                        <div
                          className="h-full rounded-full bg-primary"
                          style={{ width: `${(d.open_incidents / max) * 100}%` }}
                        />
                      </div>
                      <span className="w-8 text-right font-medium">{d.open_incidents}</span>
                      <Badge variant="outline" className="text-xs">{d.staff_count} staff</Badge>
                    </li>
                  );
                })}
                {data.departments.length === 0 && (
                  <li className="text-sm text-muted-foreground">No departments configured.</li>
                )}
              </ul>
            )}
          </CardContent>
        </Card>

        {/* Governance quick links */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Manage</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2 sm:grid-cols-2">
            <Link to="/queue?status=submitted">
              <Button variant="outline" className="w-full justify-start">
                <FileClock className="h-4 w-4" /> Verify queue
              </Button>
            </Link>
            <Link to="/analytics">
              <Button variant="outline" className="w-full justify-start">
                <BarChart3 className="h-4 w-4" /> Analytics
              </Button>
            </Link>
            <Link to="/admin/users">
              <Button variant="outline" className="w-full justify-start">
                <Users className="h-4 w-4" /> Users
              </Button>
            </Link>
            <Link to="/admin/announcements">
              <Button variant="outline" className="w-full justify-start">
                <Megaphone className="h-4 w-4" /> Announcements
              </Button>
            </Link>
            <Link to="/admin/audit">
              <Button variant="outline" className="w-full justify-start">
                <ScrollText className="h-4 w-4" /> Audit log
              </Button>
            </Link>
            <a href="/admin/django/" target="_blank" rel="noreferrer">
              <Button variant="outline" className="w-full justify-start">
                <UserCog className="h-4 w-4" /> Django admin
              </Button>
            </a>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* SLA Breaches - most critical */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base text-danger">
              <AlertCircle className="h-4 w-4" aria-hidden /> SLA Breaches (Top 10)
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isPending || !data ? (
              <Skeleton className="h-40 w-full" />
            ) : data.sla_breaches.length === 0 ? (
              <p className="text-sm text-success">No SLA breaches — all on track!</p>
            ) : (
              <ul className="space-y-2">
                {data.sla_breaches.map((b) => (
                  <li key={b.id} className="flex items-center justify-between gap-3 py-2 text-sm border-b last:border-0">
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium">{b.reference} — {b.title}</p>
                      <p className="truncate text-xs text-muted-foreground">{b.department}</p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge variant="danger">{b.overdue_hours}h overdue</Badge>
                      <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => window.location.href = `/incidents/${b.id}`}>
                        <Eye className="h-3 w-3" />
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        {/* Incident breakdowns */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Gauge className="h-4 w-4 text-primary" aria-hidden /> Top categories & wards
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isPending || !data ? (
              <Skeleton className="h-40 w-full" />
            ) : (
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="text-xs text-muted-foreground mb-2">By category</p>
                  <ul className="space-y-1 max-h-48 overflow-y-auto">
                    {data.incidents.by_category.map((c, i) => (
                      <li key={i} className="flex items-center justify-between text-sm py-1">
                        <span className="truncate">{c.name || "Uncategorized"}</span>
                        <span className="font-medium text-primary">{c.count}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-2">By ward</p>
                  <ul className="space-y-1 max-h-48 overflow-y-auto">
                    {data.incidents.by_ward.map((w, i) => (
                      <li key={i} className="flex items-center justify-between text-sm py-1">
                        <span className="truncate">{w.name || "Unknown ward"}</span>
                        <span className="font-medium text-primary">{w.count}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Deletion requests */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertTriangle className="h-4 w-4 text-warning" aria-hidden /> Pending deletion
              requests
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isPending || !data ? (
              <Skeleton className="h-24 w-full" />
            ) : data.deletion_requests.length === 0 ? (
              <p className="text-sm text-muted-foreground">No pending requests.</p>
            ) : (
              <ul className="divide-y">
                {data.deletion_requests.map((r) => (
                  <li key={r.id} className="flex items-center justify-between gap-3 py-2 text-sm">
                    <div className="min-w-0">
                      <p className="truncate font-medium">{r.email}</p>
                      <p className="truncate text-xs text-muted-foreground">
                        {r.reason || "No reason given"} · {timeAgo(r.requested_at)}
                      </p>
                    </div>
                    <div className="flex gap-1">
                      <Button size="sm" variant="outline" onClick={() => {}}>Approve</Button>
                      <Button size="sm" variant="ghost" onClick={() => {}}>Reject</Button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        {/* Recent audit */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Latest admin activity</CardTitle>
          </CardHeader>
          <CardContent>
            {isPending || !data ? (
              <Skeleton className="h-24 w-full" />
            ) : data.recent_audit.length === 0 ? (
              <p className="text-sm text-muted-foreground">No audit entries yet.</p>
            ) : (
              <ul className="divide-y">
                {data.recent_audit.map((a) => (
                  <li key={a.id} className="flex items-center justify-between gap-3 py-2 text-sm">
                    <span className="truncate font-mono text-xs">{a.action}</span>
                    <span className="shrink-0 text-xs text-muted-foreground">
                      {a.actor ?? "system"} · {timeAgo(a.created_at)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
