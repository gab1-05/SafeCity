import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, CheckCheck } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState, Skeleton } from "@/components/ui/feedback";
import { notificationsApi } from "@/api/auth";
import { timeAgo } from "@/lib/utils";

export function NotificationsPage() {
  const queryClient = useQueryClient();
  const { data, isPending } = useQuery({
    queryKey: ["notifications"],
    queryFn: notificationsApi.list,
  });

  const markRead = async (id: string) => {
    await notificationsApi.markRead(id);
    queryClient.invalidateQueries({ queryKey: ["notifications"] });
  };

  const markAll = async () => {
    await notificationsApi.markAllRead();
    queryClient.invalidateQueries({ queryKey: ["notifications"] });
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Notifications</h1>
          <p className="text-sm text-muted-foreground">
            {data?.unread_count ?? 0} unread
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={markAll} disabled={!data?.unread_count}>
          <CheckCheck className="h-4 w-4" /> Mark all read
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isPending && (
            <div className="space-y-2 p-4">
              <Skeleton className="h-14 w-full" />
              <Skeleton className="h-14 w-full" />
            </div>
          )}
          {data?.results.length === 0 && (
            <div className="p-6">
              <EmptyState
                title="No notifications yet"
                description="Updates about your reports will appear here."
              />
            </div>
          )}
          <ul className="divide-y">
            {data?.results.map((n) => (
              <li
                key={n.id}
                className={`flex items-start gap-3 p-4 ${!n.read_at ? "bg-primary/5" : ""}`}
              >
                <Bell className={`mt-1 h-4 w-4 shrink-0 ${n.read_at ? "text-muted-foreground" : "text-primary"}`} aria-hidden />
                <div className="min-w-0 flex-1">
                  <p className="font-medium">{n.title}</p>
                  {n.body && <p className="text-sm text-muted-foreground">{n.body}</p>}
                  <p className="mt-0.5 text-xs text-muted-foreground">{timeAgo(n.created_at)}</p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {n.incident_id && (
                    <Link
                      to={`/incidents/${n.incident_id}`}
                      className="text-xs text-primary hover:underline"
                    >
                      View
                    </Link>
                  )}
                  {!n.read_at && (
                    <Button variant="ghost" size="sm" onClick={() => markRead(n.id)}>
                      Mark read
                    </Button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
