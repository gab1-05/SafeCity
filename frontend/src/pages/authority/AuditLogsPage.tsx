import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Input, Select } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton, ErrorState, EmptyState } from "@/components/ui/feedback";
import { Badge } from "@/components/ui/badge";
import client from "@/api/client";
import { formatDate } from "@/lib/utils";

interface AuditEntry {
  id: string;
  actor: string | null;
  action: string;
  object_type: string;
  object_id: string;
  changes: Record<string, unknown>;
  request_id: string;
  ip_address: string | null;
  created_at: string;
}

export function AuditLogsPage() {
  const [action, setAction] = useState("");
  const [limit, setLimit] = useState(100);

  const { data, isPending, isError, refetch } = useQuery({
    queryKey: ["audit-logs", action, limit],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (action) params.set("action", action);
      params.set("limit", String(limit));
      const { data } = await client.get(`/audit-logs/?${params}`);
      return data as AuditEntry[];
    },
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Audit logs</h1>
        <p className="text-sm text-muted-foreground">
          Immutable record of every state-changing action. Read-only.
        </p>
      </div>

      <div className="flex gap-2">
        <Input
          placeholder="Filter by action (e.g. incident.)"
          value={action}
          onChange={(e) => setAction(e.target.value)}
          className="w-64"
          aria-label="Filter by action"
        />
        <Select
          value={String(limit)}
          onChange={(e) => setLimit(Number(e.target.value))}
          className="w-32"
          aria-label="Result limit"
        >
          <option value="50">50 rows</option>
          <option value="100">100 rows</option>
          <option value="300">300 rows</option>
        </Select>
        <Button variant="outline" onClick={() => refetch()}>
          Refresh
        </Button>
      </div>

      {isPending && <Skeleton className="h-72 w-full" />}
      {isError && <ErrorState message="Could not load audit logs." onRetry={refetch} />}
      {data?.length === 0 && (
        <EmptyState title="No audit entries match" description="Try a broader filter." />
      )}

      {data && data.length > 0 && (
        <Card>
          <CardContent className="overflow-x-auto p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50 text-left">
                  <th className="p-3 font-medium">When</th>
                  <th className="p-3 font-medium">Actor</th>
                  <th className="p-3 font-medium">Action</th>
                  <th className="p-3 font-medium">Object</th>
                  <th className="p-3 font-medium">IP</th>
                  <th className="p-3 font-medium">Request ID</th>
                </tr>
              </thead>
              <tbody>
                {data.map((entry) => (
                  <tr key={entry.id} className="border-b align-top hover:bg-accent/40">
                    <td className="whitespace-nowrap p-3 text-xs">{formatDate(entry.created_at)}</td>
                    <td className="p-3 text-xs">{entry.actor ?? "system"}</td>
                    <td className="p-3">
                      <Badge variant="outline">{entry.action}</Badge>
                    </td>
                    <td className="p-3 font-mono text-xs">
                      {entry.object_type}
                      {entry.object_id ? `#${entry.object_id.slice(0, 8)}` : ""}
                    </td>
                    <td className="p-3 text-xs">{entry.ip_address ?? "—"}</td>
                    <td className="p-3 font-mono text-xs">{entry.request_id.slice(0, 8)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
